# -*- coding: utf-8 -*-
"""Trusted xG source intake and target compatibility reporting.

Phase 13.3 diagnostic/foundation only. This module evaluates user-supplied
trusted xG CSVs against local target files without inferring xG values or
modifying production manifests.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.importers.manual_xg_acceptance import (
    MANUAL_XG_ACCEPTED,
    MANUAL_XG_ACCEPTED_WITH_WARNINGS,
    evaluate_manual_xg_acceptance,
)
from football_prediction_v19.importers.manual_xg_template_generator import build_manual_xg_entry_template
from football_prediction_v19.importers.trusted_xg_manifest_promotion import (
    TRUSTED_XG_PROMOTION_BLOCKED_ACCEPTANCE_FAILED,
    TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE,
    TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE,
    TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG,
    TRUSTED_XG_PROMOTION_READY,
    TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS,
)
from football_prediction_v19.importers.trusted_xg_source import (
    UNKNOWN_SCHEMA,
    detect_trusted_xg_source_schema,
    join_trusted_xg_to_manual_template,
    normalize_trusted_xg_source,
)

TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW = "TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW"
TRUSTED_XG_INTAKE_READY_FOR_FILL_PREVIEW = "TRUSTED_XG_INTAKE_READY_FOR_FILL_PREVIEW"
TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA = "TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA"
TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH = "TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH"
TRUSTED_XG_INTAKE_BLOCKED_MISSING_XG_COVERAGE = "TRUSTED_XG_INTAKE_BLOCKED_MISSING_XG_COVERAGE"
TRUSTED_XG_INTAKE_NO_SOURCES_FOUND = "TRUSTED_XG_INTAKE_NO_SOURCES_FOUND"

READY_PROMOTION_LABELS = {TRUSTED_XG_PROMOTION_READY, TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS}


@dataclass(frozen=True)
class TrustedXGIntakeResult:
    source_path: str
    source_file: str
    detected_schema: str
    source_rows: int
    valid_source: bool
    candidate_targets_checked: int
    best_target_path: str
    best_target_file: str
    best_rows_template: int
    best_rows_filled: int
    best_rows_missing_xg: int
    best_fill_coverage_pct: float
    best_join_coverage_pct: float
    best_promotion_label: str
    intake_label: str
    recommended_command: str
    blocking_reasons: list[str]
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _is_demo_or_template(path: Path) -> bool:
    lowered_parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    return (
        any(part in {"examples", "example", "templates", "template", "demo", "samples", "sample"} for part in lowered_parts)
        or any(token in name for token in ("template", "sample", "demo", "example"))
    )


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    return out


def discover_trusted_xg_sources(source_dir: str | Path = "data/trusted_xg_sources") -> list[Path]:
    root = _repo_root()
    source_root = Path(source_dir)
    if not source_root.is_absolute():
        source_root = root / source_root
    if not source_root.exists():
        return []
    return [path for path in _unique(sorted(source_root.glob("*.csv"))) if not _is_demo_or_template(path)]


def discover_candidate_targets(root: str | Path | None = None) -> list[Path]:
    repo = Path(root) if root is not None else _repo_root()
    paths: list[Path] = []
    for pattern in (
        repo / "data" / "processed" / "*_clean.csv",
        repo / "data" / "upcoming*_fixtures*.csv",
        repo / "data" / "raw" / "*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return [path for path in _unique(paths) if not _is_demo_or_template(path)]


def _empty_result(source_path: str | Path, label: str, blocking: list[str], schema: str = UNKNOWN_SCHEMA, source_rows: int = 0) -> TrustedXGIntakeResult:
    path = Path(source_path)
    return TrustedXGIntakeResult(
        source_path=str(path),
        source_file=path.name,
        detected_schema=schema,
        source_rows=int(source_rows),
        valid_source=False,
        candidate_targets_checked=0,
        best_target_path="",
        best_target_file="",
        best_rows_template=0,
        best_rows_filled=0,
        best_rows_missing_xg=0,
        best_fill_coverage_pct=0.0,
        best_join_coverage_pct=0.0,
        best_promotion_label=TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE,
        intake_label=label,
        recommended_command="",
        blocking_reasons=blocking,
        warning_notes=[],
    )


def _promotion_label(acceptance_label: str, blocking: list[str], rows_missing_xg: int) -> str:
    if rows_missing_xg:
        return TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG
    if acceptance_label == MANUAL_XG_ACCEPTED:
        return TRUSTED_XG_PROMOTION_READY
    if acceptance_label == MANUAL_XG_ACCEPTED_WITH_WARNINGS:
        return TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS
    if "LOW_JOIN_COVERAGE" in blocking:
        return TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE
    if acceptance_label:
        return TRUSTED_XG_PROMOTION_BLOCKED_ACCEPTANCE_FAILED
    return TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE


def _command(source: Path, target: Path, mode: str = "fill") -> str:
    if not target:
        return ""
    quoted_source = f'"{source}"'
    quoted_target = f'"{target}"'
    if mode == "promotion":
        return (
            f"python scripts/promote_trusted_xg_to_manifest.py --source-xg {quoted_source} "
            f"--template-source {quoted_target} --target {quoted_target}"
        )
    return f"python scripts/fill_manual_xg_from_trusted_source.py --source {quoted_source} --template {quoted_target} --target {quoted_target}"


def evaluate_trusted_xg_source_against_target(source_path: str | Path, target_path: str | Path) -> dict[str, Any]:
    source_path = Path(source_path)
    target_path = Path(target_path)
    source_df = pd.read_csv(source_path, low_memory=False)
    target_df = pd.read_csv(target_path, low_memory=False)
    normalized_source = normalize_trusted_xg_source(source_df, source_path=source_path)
    template_df, template_result = build_manual_xg_entry_template(target_df, source_path=target_path)
    filled = join_trusted_xg_to_manual_template(normalized_source, template_df)
    rows_template = int(filled.attrs.get("rows_template", len(filled)))
    rows_filled = int(filled.attrs.get("rows_filled", 0))
    rows_missing = int(filled.attrs.get("rows_missing_xg", rows_template - rows_filled))
    fill_coverage = float(filled.attrs.get("join_coverage_pct", 0.0))
    acceptance_label = ""
    join_coverage = 0.0
    blocking: list[str] = []
    warnings: list[str] = list(template_result.warning_notes)
    if rows_template == 0 or rows_filled == 0:
        blocking.append("NO_TARGET_MATCH")
    elif rows_missing:
        blocking.append("MISSING_XG_AFTER_TRUSTED_SOURCE_FILL")
    else:
        _joined, acceptance = evaluate_manual_xg_acceptance(
            filled,
            target_df=target_df,
            source_path=source_path,
            target_path=target_path,
        )
        acceptance_label = acceptance.acceptance_label
        join_coverage = acceptance.join_coverage_pct
        blocking.extend(acceptance.blocking_reasons)
        warnings.extend(acceptance.warning_notes)
    promotion = _promotion_label(acceptance_label, blocking, rows_missing)
    return {
        "target_path": str(target_path),
        "target_file": target_path.name,
        "rows_template": rows_template,
        "rows_filled": rows_filled,
        "rows_missing_xg": rows_missing,
        "fill_coverage_pct": round(fill_coverage, 2),
        "join_coverage_pct": round(join_coverage, 2),
        "promotion_label": promotion,
        "blocking_reasons": sorted(set(blocking)),
        "warning_notes": sorted(set(warnings)),
    }


def _best_match(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda row: (
            row["promotion_label"] in READY_PROMOTION_LABELS,
            float(row.get("fill_coverage_pct", 0.0)),
            int(row.get("rows_filled", 0)),
            -int(row.get("rows_missing_xg", 0)),
        ),
        reverse=True,
    )[0]


def evaluate_trusted_xg_source_intake(source_path: str | Path, targets: list[Path] | None = None) -> TrustedXGIntakeResult:
    source_path = Path(source_path)
    try:
        source_df = pd.read_csv(source_path, low_memory=False)
        schema = detect_trusted_xg_source_schema(source_df)
        normalized = normalize_trusted_xg_source(source_df, source_path=source_path)
    except Exception as exc:
        rows = int(len(source_df)) if "source_df" in locals() else 0
        return _empty_result(source_path, TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA, [str(exc)], source_rows=rows)
    if schema == UNKNOWN_SCHEMA:
        return _empty_result(source_path, TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA, ["INVALID_TRUSTED_XG_SOURCE_SCHEMA"], schema=schema, source_rows=len(source_df))

    targets = targets if targets is not None else discover_candidate_targets()
    matches: list[dict[str, Any]] = []
    for target in targets:
        try:
            matches.append(evaluate_trusted_xg_source_against_target(source_path, target))
        except Exception as exc:
            matches.append({
                "target_path": str(target),
                "target_file": target.name,
                "rows_template": 0,
                "rows_filled": 0,
                "rows_missing_xg": 0,
                "fill_coverage_pct": 0.0,
                "join_coverage_pct": 0.0,
                "promotion_label": TRUSTED_XG_PROMOTION_BLOCKED_ACCEPTANCE_FAILED,
                "blocking_reasons": [str(exc)],
                "warning_notes": [],
            })
    best = _best_match(matches)
    if best is None or int(best.get("rows_filled", 0)) == 0:
        label = TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH
    elif best["promotion_label"] in READY_PROMOTION_LABELS:
        label = TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW
    elif int(best.get("rows_missing_xg", 0)) > 0:
        label = TRUSTED_XG_INTAKE_BLOCKED_MISSING_XG_COVERAGE
    else:
        label = TRUSTED_XG_INTAKE_READY_FOR_FILL_PREVIEW

    best = best or {}
    command_mode = "promotion" if label == TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW else "fill"
    target_path = Path(str(best.get("target_path", ""))) if best.get("target_path") else None
    return TrustedXGIntakeResult(
        source_path=str(source_path),
        source_file=source_path.name,
        detected_schema=str(normalized["xg_source_schema"].iloc[0]) if not normalized.empty else schema,
        source_rows=int(len(normalized)),
        valid_source=True,
        candidate_targets_checked=len(targets),
        best_target_path=str(best.get("target_path", "")),
        best_target_file=str(best.get("target_file", "")),
        best_rows_template=int(best.get("rows_template", 0)),
        best_rows_filled=int(best.get("rows_filled", 0)),
        best_rows_missing_xg=int(best.get("rows_missing_xg", 0)),
        best_fill_coverage_pct=float(best.get("fill_coverage_pct", 0.0)),
        best_join_coverage_pct=float(best.get("join_coverage_pct", 0.0)),
        best_promotion_label=str(best.get("promotion_label", "")),
        intake_label=label,
        recommended_command=_command(source_path, target_path, command_mode) if target_path else "",
        blocking_reasons=list(best.get("blocking_reasons", [])),
        warning_notes=list(best.get("warning_notes", [])),
    )


def build_trusted_xg_intake_report(source_dir: str | Path = "data/trusted_xg_sources") -> pd.DataFrame:
    sources = discover_trusted_xg_sources(source_dir)
    if not sources:
        return pd.DataFrame([TrustedXGIntakeResult(
            source_path="",
            source_file="",
            detected_schema="",
            source_rows=0,
            valid_source=False,
            candidate_targets_checked=0,
            best_target_path="",
            best_target_file="",
            best_rows_template=0,
            best_rows_filled=0,
            best_rows_missing_xg=0,
            best_fill_coverage_pct=0.0,
            best_join_coverage_pct=0.0,
            best_promotion_label="",
            intake_label=TRUSTED_XG_INTAKE_NO_SOURCES_FOUND,
            recommended_command="",
            blocking_reasons=["NO_TRUSTED_XG_SOURCE_FILES"],
            warning_notes=[],
        ).to_dict()])
    targets = discover_candidate_targets()
    rows = [evaluate_trusted_xg_source_intake(source, targets=targets).to_dict() for source in sources]
    return pd.DataFrame(rows)


def trusted_xg_intake_recommendation(rows: pd.DataFrame) -> str:
    if rows.empty or rows["intake_label"].astype(str).eq(TRUSTED_XG_INTAKE_NO_SOURCES_FOUND).any():
        return "ADD_TRUSTED_XG_SOURCE_FILE"
    labels = rows["intake_label"].astype(str)
    if labels.eq(TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW).any():
        return "READY_FOR_TRUSTED_XG_PROMOTION_PREVIEW"
    if labels.eq(TRUSTED_XG_INTAKE_READY_FOR_FILL_PREVIEW).any():
        return "READY_FOR_TRUSTED_XG_FILL_PREVIEW"
    if labels.eq(TRUSTED_XG_INTAKE_BLOCKED_MISSING_XG_COVERAGE).any():
        return "FILL_MISSING_XG_FROM_TRUSTED_SOURCE"
    if labels.eq(TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH).any() and rows["valid_source"].astype(bool).any():
        return "FIX_TRUSTED_XG_TARGET_MATCHING"
    if labels.eq(TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA).all():
        return "FIX_TRUSTED_XG_SOURCE_SCHEMA"
    return "INCONCLUSIVE_TRUSTED_XG_INTAKE"
