# -*- coding: utf-8 -*-
"""Acceptance gate for filled manual xG CSV files.

Diagnostic/foundation only. No xG values are inferred, filled, deleted, or
written back to source data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.importers.manual_xg_csv import normalize_manual_xg_dataframe
from football_prediction_v19.xg_join_preview import JOIN_READY, JOIN_READY_WITH_WARNINGS, preview_xg_join

MANUAL_XG_ACCEPTED = "MANUAL_XG_ACCEPTED"
MANUAL_XG_ACCEPTED_WITH_WARNINGS = "MANUAL_XG_ACCEPTED_WITH_WARNINGS"
MANUAL_XG_REJECTED_MISSING_VALUES = "MANUAL_XG_REJECTED_MISSING_VALUES"
MANUAL_XG_REJECTED_INVALID_VALUES = "MANUAL_XG_REJECTED_INVALID_VALUES"
MANUAL_XG_REJECTED_DUPLICATE_KEYS = "MANUAL_XG_REJECTED_DUPLICATE_KEYS"
MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE = "MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE"
MANUAL_XG_REJECTED_INVALID_SCHEMA = "MANUAL_XG_REJECTED_INVALID_SCHEMA"
MANUAL_XG_TEMPLATE_ONLY = "MANUAL_XG_TEMPLATE_ONLY"
MANUAL_XG_NO_TARGET_PROVIDED = "MANUAL_XG_NO_TARGET_PROVIDED"


@dataclass(frozen=True)
class ManualXGAcceptanceResult:
    source_path: str
    target_path: str
    rows_source: int
    rows_valid: int
    rows_invalid: int
    rows_join_matched: int
    join_coverage_pct: float
    missing_xg_count: int
    non_numeric_xg_count: int
    negative_xg_count: int
    duplicate_key_count: int
    missing_identity_count: int
    acceptance_label: str
    blocking_reasons: list[str]
    warning_notes: list[str]
    preview_output_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm_col(name: Any) -> str:
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {_norm_col(col): str(col) for col in df.columns}
    for name in names:
        key = _norm_col(name)
        if key in by_norm:
            return by_norm[key]
    return None


def _xg_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    return (
        _find_col(df, "home_xg", "xG_home", "hxg"),
        _find_col(df, "away_xg", "xG_away", "axg"),
    )


def _identity_missing_count(normalized: pd.DataFrame) -> int:
    if not {"date", "home_team", "away_team"}.issubset(normalized.columns):
        return len(normalized)
    identity = normalized[["date", "home_team", "away_team"]]
    mask = identity.isna().any(axis=1) | identity.astype(str).apply(lambda col: col.str.strip().eq("")).any(axis=1)
    return int(mask.sum())


def _duplicate_key_count(normalized: pd.DataFrame) -> int:
    if not {"date", "home_team", "away_team"}.issubset(normalized.columns):
        return 0
    keys = (
        normalized["date"].astype(str).str.strip()
        + "|"
        + normalized["home_team"].astype(str).str.strip().str.lower()
        + "|"
        + normalized["away_team"].astype(str).str.strip().str.lower()
    )
    return int(keys.duplicated(keep=False).sum())


def validate_filled_manual_xg_values(df: pd.DataFrame) -> dict[str, Any]:
    rows_source = int(len(df))
    try:
        normalized = normalize_manual_xg_dataframe(df)
    except ValueError:
        return {
            "normalized": pd.DataFrame(),
            "rows_source": rows_source,
            "rows_valid": 0,
            "rows_invalid": rows_source,
            "missing_xg_count": rows_source,
            "non_numeric_xg_count": 0,
            "negative_xg_count": 0,
            "duplicate_key_count": 0,
            "missing_identity_count": rows_source,
            "blocking_reasons": ["INVALID_SCHEMA"],
        }

    home_xg, away_xg = _xg_columns(df)
    raw_xg = df[[home_xg, away_xg]].copy() if home_xg and away_xg else pd.DataFrame(index=df.index)
    missing_mask = raw_xg.isna().any(axis=1) | raw_xg.astype(str).apply(lambda col: col.str.strip().eq("")).any(axis=1)
    numeric_xg = raw_xg.apply(pd.to_numeric, errors="coerce") if not raw_xg.empty else pd.DataFrame(index=df.index)
    non_numeric_mask = numeric_xg.isna().any(axis=1) & ~missing_mask if not numeric_xg.empty else pd.Series(False, index=df.index)
    negative_mask = (numeric_xg < 0).any(axis=1) if not numeric_xg.empty else pd.Series(False, index=df.index)
    missing_identity_count = _identity_missing_count(normalized)
    duplicate_key_count = _duplicate_key_count(normalized)
    invalid_mask = missing_mask | non_numeric_mask | negative_mask
    if missing_identity_count:
        invalid_mask = invalid_mask | (
            normalized[["date", "home_team", "away_team"]].isna().any(axis=1)
            | normalized[["date", "home_team", "away_team"]].astype(str).apply(lambda col: col.str.strip().eq("")).any(axis=1)
        )
    blocking: list[str] = []
    if int(missing_mask.sum()):
        blocking.append("MISSING_XG_VALUES")
    if int(non_numeric_mask.sum()):
        blocking.append("NON_NUMERIC_XG_VALUES")
    if int(negative_mask.sum()):
        blocking.append("NEGATIVE_XG_VALUES")
    if duplicate_key_count:
        blocking.append("DUPLICATE_MATCH_KEYS")
    if missing_identity_count:
        blocking.append("MISSING_IDENTITY_VALUES")
    return {
        "normalized": normalized,
        "rows_source": rows_source,
        "rows_valid": int(rows_source - invalid_mask.sum()) if not duplicate_key_count and not missing_identity_count else 0,
        "rows_invalid": int(invalid_mask.sum()) if not duplicate_key_count else rows_source,
        "missing_xg_count": int(missing_mask.sum()),
        "non_numeric_xg_count": int(non_numeric_mask.sum()),
        "negative_xg_count": int(negative_mask.sum()),
        "duplicate_key_count": duplicate_key_count,
        "missing_identity_count": missing_identity_count,
        "blocking_reasons": blocking,
    }


def detect_manual_xg_template_only(df: pd.DataFrame, path: str | Path | None = None) -> bool:
    name_hint = path is not None and ("template" in Path(path).name.lower() or "sample" in Path(path).name.lower())
    if name_hint:
        return True
    home_xg, away_xg = _xg_columns(df)
    if not home_xg or not away_xg or df.empty:
        return False
    raw_xg = df[[home_xg, away_xg]]
    all_blank = (raw_xg.isna() | raw_xg.astype(str).apply(lambda col: col.str.strip().eq(""))).all().all()
    status_col = _find_col(df, "xg_entry_status")
    status_hint = status_col is not None and df[status_col].astype(str).str.contains("NEEDS_MANUAL_ENTRY", na=False).any()
    return bool(all_blank and status_hint)


def _label_from_blockers(metrics: dict[str, Any], template_only: bool) -> str:
    if template_only:
        return MANUAL_XG_TEMPLATE_ONLY
    if "INVALID_SCHEMA" in metrics["blocking_reasons"] or metrics["missing_identity_count"]:
        return MANUAL_XG_REJECTED_INVALID_SCHEMA
    if metrics["duplicate_key_count"]:
        return MANUAL_XG_REJECTED_DUPLICATE_KEYS
    if metrics["missing_xg_count"]:
        return MANUAL_XG_REJECTED_MISSING_VALUES
    if metrics["non_numeric_xg_count"] or metrics["negative_xg_count"]:
        return MANUAL_XG_REJECTED_INVALID_VALUES
    return ""


def evaluate_manual_xg_acceptance(
    xg_df: pd.DataFrame,
    target_df: pd.DataFrame | None = None,
    source_path: str | Path | None = None,
    target_path: str | Path | None = None,
    min_join_coverage: float = 95.0,
) -> tuple[pd.DataFrame, ManualXGAcceptanceResult]:
    metrics = validate_filled_manual_xg_values(xg_df)
    template_only = detect_manual_xg_template_only(xg_df, path=source_path)
    label = _label_from_blockers(metrics, template_only)
    joined = pd.DataFrame()
    join_matched = 0
    join_coverage = 0.0
    warnings: list[str] = []
    blocking = list(metrics["blocking_reasons"])

    if not label:
        if target_df is None:
            label = MANUAL_XG_NO_TARGET_PROVIDED
            blocking.append("NO_TARGET_PROVIDED")
        else:
            joined, join_result = preview_xg_join(metrics["normalized"], target_df, target_type="manual_xg_acceptance")
            join_matched = join_result.matched_rows
            join_coverage = join_result.join_coverage_pct
            warnings.extend(join_result.warning_notes)
            if join_coverage < min_join_coverage:
                label = MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE
                blocking.append("LOW_JOIN_COVERAGE")
            elif join_result.join_quality_label == JOIN_READY_WITH_WARNINGS or warnings:
                label = MANUAL_XG_ACCEPTED_WITH_WARNINGS
            elif join_result.join_quality_label == JOIN_READY:
                label = MANUAL_XG_ACCEPTED
            else:
                label = MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE
                blocking.append("LOW_JOIN_COVERAGE")

    result = ManualXGAcceptanceResult(
        source_path=str(source_path or ""),
        target_path=str(target_path or ""),
        rows_source=int(metrics["rows_source"]),
        rows_valid=int(metrics["rows_valid"]) if label not in {MANUAL_XG_TEMPLATE_ONLY, MANUAL_XG_REJECTED_INVALID_SCHEMA} else 0,
        rows_invalid=int(metrics["rows_invalid"]),
        rows_join_matched=int(join_matched),
        join_coverage_pct=float(join_coverage),
        missing_xg_count=int(metrics["missing_xg_count"]),
        non_numeric_xg_count=int(metrics["non_numeric_xg_count"]),
        negative_xg_count=int(metrics["negative_xg_count"]),
        duplicate_key_count=int(metrics["duplicate_key_count"]),
        missing_identity_count=int(metrics["missing_identity_count"]),
        acceptance_label=label,
        blocking_reasons=sorted(set(blocking)),
        warning_notes=sorted(set(warnings)),
        preview_output_path="",
    )
    return joined, result


def write_manual_xg_acceptance_preview(
    xg_df: pd.DataFrame,
    target_df: pd.DataFrame,
    result: ManualXGAcceptanceResult,
    output_dir: str | Path = "outputs/xg_acceptance_preview",
) -> Path:
    source = Path(result.source_path or "manual_xg.csv")
    target = Path(result.target_path or "target.csv")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / f"{source.stem}__to__{target.stem}_xg_acceptance_preview.csv").resolve()
    if result.source_path and output == source.resolve():
        raise ValueError("acceptance preview must not overwrite source file")
    if result.target_path and output == target.resolve():
        raise ValueError("acceptance preview must not overwrite target file")
    if output_root.resolve() not in output.parents:
        raise ValueError("acceptance preview must stay under output_dir")
    joined, _join_result = preview_xg_join(xg_df, target_df, target_type="manual_xg_acceptance")
    joined.to_csv(output, index=False)
    return output


def run_manual_xg_acceptance_gate(
    xg_path: str | Path,
    target_path: str | Path | None = None,
    output_dir: str | Path = "outputs/xg_acceptance_preview",
    min_join_coverage: float = 95.0,
    *,
    write_preview: bool = True,
) -> ManualXGAcceptanceResult:
    xg_df = pd.read_csv(xg_path, low_memory=False)
    target_df = pd.read_csv(target_path, low_memory=False) if target_path is not None else None
    joined, result = evaluate_manual_xg_acceptance(
        xg_df,
        target_df=target_df,
        source_path=xg_path,
        target_path=target_path,
        min_join_coverage=min_join_coverage,
    )
    preview_output_path = ""
    if write_preview and target_df is not None and not joined.empty:
        preview_output_path = str(write_manual_xg_acceptance_preview(
            xg_df if result.acceptance_label.startswith("MANUAL_XG_REJECTED") else validate_filled_manual_xg_values(xg_df)["normalized"],
            target_df,
            result,
            output_dir=output_dir,
        ))
    return ManualXGAcceptanceResult(**{**result.to_dict(), "preview_output_path": preview_output_path})
