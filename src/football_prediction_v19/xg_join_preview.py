# -*- coding: utf-8 -*-
"""Manual xG join preview helpers.

Diagnostic/foundation only. No xG values are inferred, invented, or written
back to source data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

JOIN_READY = "JOIN_READY"
JOIN_READY_WITH_WARNINGS = "JOIN_READY_WITH_WARNINGS"
JOIN_BLOCKED_DUPLICATE_KEYS = "JOIN_BLOCKED_DUPLICATE_KEYS"
JOIN_BLOCKED_AMBIGUOUS_MATCHES = "JOIN_BLOCKED_AMBIGUOUS_MATCHES"
JOIN_LOW_COVERAGE = "JOIN_LOW_COVERAGE"
JOIN_NO_MATCHES = "JOIN_NO_MATCHES"
JOIN_INVALID_INPUT = "JOIN_INVALID_INPUT"


@dataclass(frozen=True)
class XGJoinPreviewResult:
    xg_source_path: str
    target_path: str
    target_type: str
    rows_xg: int
    rows_target: int
    matched_rows: int
    unmatched_xg_rows: int
    unmatched_target_rows: int
    duplicate_xg_keys: int
    duplicate_target_keys: int
    ambiguous_matches: int
    join_coverage_pct: float
    join_quality_label: str
    output_path: str
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm_col(name: Any) -> str:
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {_norm_col(col): str(col) for col in df.columns}
    for name in names:
        if _norm_col(name) in by_norm:
            return by_norm[_norm_col(name)]
    return None


def _norm_team(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace(".", "").split())


def normalize_join_key_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    date = _find_col(out, "date", "Date")
    home = _find_col(out, "home_team", "HomeTeam", "home")
    away = _find_col(out, "away_team", "AwayTeam", "away")
    if date is not None:
        parsed = pd.to_datetime(out[date], errors="coerce", format="mixed", dayfirst=False)
        if parsed.isna().any():
            fallback = pd.to_datetime(out[date], errors="coerce", format="mixed", dayfirst=True)
            parsed = parsed.fillna(fallback)
        out["date"] = parsed.dt.strftime("%Y-%m-%d")
    if home is not None:
        out["home_team"] = out[home]
    if away is not None:
        out["away_team"] = out[away]
    return out


def build_match_key(df: pd.DataFrame) -> pd.Series:
    normalized = normalize_join_key_columns(df)
    missing = [col for col in ("date", "home_team", "away_team") if col not in normalized.columns]
    if missing:
        raise ValueError("missing join key columns: " + ", ".join(missing))
    return (
        normalized["date"].astype(str).str.strip()
        + "|"
        + normalized["home_team"].map(_norm_team)
        + "|"
        + normalized["away_team"].map(_norm_team)
    )


def validate_xg_join_keys(xg_df: pd.DataFrame) -> dict[str, Any]:
    required = ["date", "home_team", "away_team", "home_xg", "away_xg"]
    normalized = normalize_join_key_columns(xg_df)
    missing = [col for col in required if col not in normalized.columns]
    duplicate_keys = 0
    if not any(col in missing for col in ("date", "home_team", "away_team")):
        keys = build_match_key(normalized)
        duplicate_keys = int(keys.duplicated(keep=False).sum())
    return {"missing_columns": missing, "duplicate_keys": duplicate_keys}


def validate_target_join_keys(target_df: pd.DataFrame) -> dict[str, Any]:
    normalized = normalize_join_key_columns(target_df)
    missing = [col for col in ("date", "home_team", "away_team") if col not in normalized.columns]
    duplicate_keys = 0
    if not missing:
        keys = build_match_key(normalized)
        duplicate_keys = int(keys.duplicated(keep=False).sum())
    return {"missing_columns": missing, "duplicate_keys": duplicate_keys}


def preview_xg_join(xg_df: pd.DataFrame, target_df: pd.DataFrame, target_type: str = "unknown") -> tuple[pd.DataFrame, XGJoinPreviewResult]:
    warnings: list[str] = []
    xg_validation = validate_xg_join_keys(xg_df)
    target_validation = validate_target_join_keys(target_df)
    rows_xg = int(len(xg_df))
    rows_target = int(len(target_df))
    if xg_validation["missing_columns"] or target_validation["missing_columns"]:
        label = JOIN_INVALID_INPUT
        joined = pd.DataFrame()
    elif xg_validation["duplicate_keys"]:
        label = JOIN_BLOCKED_DUPLICATE_KEYS
        joined = pd.DataFrame()
    elif target_validation["duplicate_keys"]:
        label = JOIN_BLOCKED_DUPLICATE_KEYS
        joined = pd.DataFrame()
    else:
        xg_norm = normalize_join_key_columns(xg_df).copy()
        target_norm = normalize_join_key_columns(target_df).copy()
        xg_norm["match_key"] = build_match_key(xg_norm)
        target_norm["match_key"] = build_match_key(target_norm)
        joined = target_norm.merge(
            xg_norm[["match_key", "home_xg", "away_xg"]],
            on="match_key",
            how="left",
            indicator=True,
        )
        matched = int((joined["_merge"] == "both").sum())
        coverage = (matched / rows_target * 100.0) if rows_target else 0.0
        if matched == 0:
            label = JOIN_NO_MATCHES
        elif coverage < 70.0:
            label = JOIN_LOW_COVERAGE
        elif coverage >= 95.0:
            label = JOIN_READY
        else:
            label = JOIN_READY_WITH_WARNINGS
            warnings.append("join coverage below 95%")
    if "joined" not in locals():
        joined = pd.DataFrame()
    matched_rows = int((joined["_merge"] == "both").sum()) if "_merge" in joined.columns else 0
    xg_keys = set(build_match_key(normalize_join_key_columns(xg_df))) if not xg_validation["missing_columns"] else set()
    target_keys = set(build_match_key(normalize_join_key_columns(target_df))) if not target_validation["missing_columns"] else set()
    coverage_pct = round((matched_rows / rows_target * 100.0), 2) if rows_target else 0.0
    result = XGJoinPreviewResult(
        xg_source_path="",
        target_path="",
        target_type=target_type,
        rows_xg=rows_xg,
        rows_target=rows_target,
        matched_rows=matched_rows,
        unmatched_xg_rows=max(0, len(xg_keys - target_keys)),
        unmatched_target_rows=max(0, rows_target - matched_rows),
        duplicate_xg_keys=int(xg_validation["duplicate_keys"]),
        duplicate_target_keys=int(target_validation["duplicate_keys"]),
        ambiguous_matches=0,
        join_coverage_pct=coverage_pct,
        join_quality_label=label,
        output_path="",
        warning_notes=warnings,
    )
    return joined, result


def write_xg_join_preview(
    joined_df: pd.DataFrame,
    source_path: str | Path,
    target_path: str | Path,
    output_dir: str | Path = "outputs/xg_join_preview",
) -> Path:
    source = Path(source_path)
    target = Path(target_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / f"{source.stem}__to__{target.stem}_xg_join_preview.csv").resolve()
    if output in {source.resolve(), target.resolve()}:
        raise ValueError("join preview must not overwrite source or target")
    if output_root.resolve() not in output.parents:
        raise ValueError("join preview must stay under output_dir")
    joined_df.to_csv(output, index=False)
    return output


def run_xg_join_preview(
    xg_path: str | Path,
    target_path: str | Path,
    output_dir: str | Path = "outputs/xg_join_preview",
    *,
    target_type: str = "unknown",
    write_preview: bool = True,
) -> XGJoinPreviewResult:
    xg_df = pd.read_csv(xg_path, low_memory=False)
    target_df = pd.read_csv(target_path, low_memory=False)
    joined, result = preview_xg_join(xg_df, target_df, target_type=target_type)
    output_path = ""
    if write_preview and not joined.empty:
        output_path = str(write_xg_join_preview(joined, xg_path, target_path, output_dir=output_dir))
    return XGJoinPreviewResult(
        **{**result.to_dict(), "xg_source_path": str(xg_path), "target_path": str(target_path), "output_path": output_path}
    )
