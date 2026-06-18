# -*- coding: utf-8 -*-
"""Trusted xG fill acceptance and manifest-entry promotion previews.

Phase 13.2 foundation only. This module writes preview artifacts only and does
not update the production manifest, model inputs, or source data.
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
from football_prediction_v19.importers.trusted_xg_source import (
    join_trusted_xg_to_manual_template,
    normalize_trusted_xg_source,
    write_filled_manual_xg_preview,
)

TRUSTED_XG_PROMOTION_READY = "TRUSTED_XG_PROMOTION_READY"
TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS = "TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS"
TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG = "TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG"
TRUSTED_XG_PROMOTION_BLOCKED_ACCEPTANCE_FAILED = "TRUSTED_XG_PROMOTION_BLOCKED_ACCEPTANCE_FAILED"
TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE = "TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE"
TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE = "TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE"
TRUSTED_XG_PROMOTION_PREVIEW_ONLY = "TRUSTED_XG_PROMOTION_PREVIEW_ONLY"

MANIFEST_ENTRY_PREVIEW_READY = "MANIFEST_ENTRY_PREVIEW_READY"
MANIFEST_ENTRY_PREVIEW_ONLY = "MANIFEST_ENTRY_PREVIEW_ONLY"
MANIFEST_ENTRY_BLOCKED_UNSAFE_PATH = "MANIFEST_ENTRY_BLOCKED_UNSAFE_PATH"
MANIFEST_ENTRY_BLOCKED_MISSING_METADATA = "MANIFEST_ENTRY_BLOCKED_MISSING_METADATA"


@dataclass(frozen=True)
class TrustedXGPromotionResult:
    source_xg_path: str
    template_source_path: str
    target_path: str
    filled_preview_path: str
    manifest_preview_path: str
    rows_template: int
    rows_filled: int
    rows_missing_xg: int
    rows_valid: int
    rows_invalid: int
    rows_join_matched: int
    join_coverage_pct: float
    acceptance_label: str
    promotion_label: str
    manifest_registration_status: str
    blocking_reasons: list[str]
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _empty_result(
    source_xg_path: str | Path,
    template_source_path: str | Path,
    target_path: str | Path,
    label: str,
    blocking: list[str],
) -> TrustedXGPromotionResult:
    return TrustedXGPromotionResult(
        source_xg_path=str(source_xg_path),
        template_source_path=str(template_source_path),
        target_path=str(target_path),
        filled_preview_path="",
        manifest_preview_path="",
        rows_template=0,
        rows_filled=0,
        rows_missing_xg=0,
        rows_valid=0,
        rows_invalid=0,
        rows_join_matched=0,
        join_coverage_pct=0.0,
        acceptance_label="",
        promotion_label=label,
        manifest_registration_status=MANIFEST_ENTRY_PREVIEW_ONLY,
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
    return TRUSTED_XG_PROMOTION_PREVIEW_ONLY


def _manifest_id(source_xg_path: str | Path, target_path: str | Path) -> str:
    return f"trusted_xg_{Path(source_xg_path).stem}_to_{Path(target_path).stem}"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _repo_relative(path: str | Path, *, root: Path | None = None) -> str:
    root = (root or _repo_root()).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("MANIFEST_PATH_OUTSIDE_REPO_ROOT") from exc


def _repo_relative_when_possible(path: str | Path, *, root: Path | None = None) -> str:
    try:
        return _repo_relative(path, root=root)
    except ValueError:
        return Path(path).name


def _is_under_outputs(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").strip().lower()
    return normalized == "outputs" or normalized.startswith("outputs/")


def _manifest_status(
    manifest_xg_path: str | Path | None,
    league: str | None,
    season: str | int | None,
    *,
    root: Path | None = None,
) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    if manifest_xg_path is None or str(manifest_xg_path).strip() == "":
        warnings.append("MANIFEST_XG_PATH_OMITTED_PREVIEW_ONLY")
        return MANIFEST_ENTRY_PREVIEW_ONLY, "", warnings
    try:
        rel = _repo_relative(manifest_xg_path, root=root)
    except ValueError:
        return MANIFEST_ENTRY_BLOCKED_UNSAFE_PATH, "", ["MANIFEST_XG_PATH_OUTSIDE_REPO_ROOT"]
    if _is_under_outputs(rel):
        return MANIFEST_ENTRY_PREVIEW_ONLY, rel, ["MANIFEST_XG_PATH_UNDER_OUTPUTS_PREVIEW_ONLY"]
    if not league or not season:
        return MANIFEST_ENTRY_BLOCKED_MISSING_METADATA, rel, ["MANIFEST_METADATA_MISSING_LEAGUE_OR_SEASON"]
    return MANIFEST_ENTRY_PREVIEW_READY, rel, warnings


def build_trusted_xg_promotion_preview(
    source_xg_path: str | Path,
    template_source_path: str | Path,
    target_path: str | Path,
    output_dir: str | Path = "outputs/xg_promotion_preview",
    min_join_coverage: float = 95.0,
) -> tuple[pd.DataFrame, TrustedXGPromotionResult]:
    try:
        source_df = pd.read_csv(source_xg_path, low_memory=False)
        template_source_df = pd.read_csv(template_source_path, low_memory=False)
        target_df = pd.read_csv(target_path, low_memory=False)
        normalized_source = normalize_trusted_xg_source(source_df, source_path=source_xg_path)
    except Exception as exc:
        return pd.DataFrame(), _empty_result(
            source_xg_path,
            template_source_path,
            target_path,
            TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE,
            [str(exc)],
        )

    template_df, template_result = build_manual_xg_entry_template(template_source_df, source_path=template_source_path)
    filled = join_trusted_xg_to_manual_template(normalized_source, template_df)
    output_root = Path(output_dir)
    filled_preview_path = str(write_filled_manual_xg_preview(
        filled,
        source_xg_path,
        template_source_path,
        output_dir=output_root,
    ))
    rows_template = int(filled.attrs.get("rows_template", len(filled)))
    rows_filled = int(filled.attrs.get("rows_filled", 0))
    rows_missing_xg = int(filled.attrs.get("rows_missing_xg", rows_template - rows_filled))
    acceptance_label = ""
    rows_valid = 0
    rows_invalid = rows_template
    rows_join_matched = 0
    join_coverage_pct = 0.0
    blocking: list[str] = []
    warnings: list[str] = list(template_result.warning_notes)
    if rows_missing_xg:
        blocking.append("MISSING_XG_AFTER_TRUSTED_SOURCE_FILL")
    else:
        _joined, acceptance = evaluate_manual_xg_acceptance(
            filled,
            target_df=target_df,
            source_path=filled_preview_path,
            target_path=target_path,
            min_join_coverage=min_join_coverage,
        )
        acceptance_label = acceptance.acceptance_label
        rows_valid = acceptance.rows_valid
        rows_invalid = acceptance.rows_invalid
        rows_join_matched = acceptance.rows_join_matched
        join_coverage_pct = acceptance.join_coverage_pct
        blocking.extend(acceptance.blocking_reasons)
        warnings.extend(acceptance.warning_notes)
    label = _promotion_label(acceptance_label, blocking, rows_missing_xg)
    result = TrustedXGPromotionResult(
        source_xg_path=str(source_xg_path),
        template_source_path=str(template_source_path),
        target_path=str(target_path),
        filled_preview_path=filled_preview_path,
        manifest_preview_path="",
        rows_template=rows_template,
        rows_filled=rows_filled,
        rows_missing_xg=rows_missing_xg,
        rows_valid=rows_valid,
        rows_invalid=rows_invalid,
        rows_join_matched=rows_join_matched,
        join_coverage_pct=join_coverage_pct,
        acceptance_label=acceptance_label,
        promotion_label=label,
        manifest_registration_status=MANIFEST_ENTRY_PREVIEW_ONLY,
        blocking_reasons=sorted(set(blocking)),
        warning_notes=sorted(set(warnings)),
    )
    return filled, result


def write_trusted_xg_manifest_entry_preview(
    result: TrustedXGPromotionResult,
    output_dir: str | Path = "outputs/xg_promotion_preview",
    *,
    manifest_xg_path: str | Path | None = None,
    league: str | None = None,
    season: str | int | None = None,
    source_name: str | None = None,
) -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / f"{_manifest_id(result.source_xg_path, result.target_path)}_manifest_entry_preview.csv").resolve()
    source = Path(result.source_xg_path)
    target = Path(result.target_path)
    template = Path(result.template_source_path)
    if output in {source.resolve(), target.resolve(), template.resolve()}:
        raise ValueError("manifest preview must not overwrite source, template, or target")
    if output_root.resolve() not in output.parents:
        raise ValueError("manifest preview must stay under output_dir")
    status, manifest_rel_path, manifest_warnings = _manifest_status(manifest_xg_path, league, season)
    target_file_path = _repo_relative_when_possible(result.target_path)
    xg_file_path = manifest_rel_path or _repo_relative_when_possible(result.filled_preview_path)
    pd.DataFrame([{
        "manifest_id": _manifest_id(result.source_xg_path, result.target_path),
        "xg_file_path": xg_file_path,
        "target_file_path": target_file_path,
        "league": league or "",
        "season": str(season or ""),
        "source_type": "MANUAL_XG_CSV",
        "source_name": source_name or "",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": result.rows_template,
        "min_join_coverage_pct": result.join_coverage_pct,
        "manifest_registration_status": status,
        "notes": "Preview only. Review before manually adding to production manifest. " + " ".join(manifest_warnings),
    }]).to_csv(output, index=False)
    return output


def run_trusted_xg_manifest_promotion(
    source_xg_path: str | Path,
    template_source_path: str | Path,
    target_path: str | Path,
    output_dir: str | Path = "outputs/xg_promotion_preview",
    min_join_coverage: float = 95.0,
    *,
    write_manifest_preview: bool = True,
    manifest_xg_path: str | Path | None = None,
    league: str | None = None,
    season: str | int | None = None,
    source_name: str | None = None,
) -> TrustedXGPromotionResult:
    _filled, result = build_trusted_xg_promotion_preview(
        source_xg_path,
        template_source_path,
        target_path,
        output_dir=output_dir,
        min_join_coverage=min_join_coverage,
    )
    manifest_preview_path = ""
    status, _manifest_rel_path, manifest_warnings = _manifest_status(manifest_xg_path, league, season)
    if (
        write_manifest_preview
        and result.promotion_label in {TRUSTED_XG_PROMOTION_READY, TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS}
    ):
        manifest_preview_path = str(write_trusted_xg_manifest_entry_preview(
            result,
            output_dir=output_dir,
            manifest_xg_path=manifest_xg_path,
            league=league,
            season=season,
            source_name=source_name,
        ))
    return TrustedXGPromotionResult(**{
        **result.to_dict(),
        "manifest_preview_path": manifest_preview_path,
        "manifest_registration_status": status,
        "warning_notes": sorted(set(result.warning_notes + manifest_warnings)),
    })
