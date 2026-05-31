# -*- coding: utf-8 -*-
"""Manual xG CSV importer skeleton.

Diagnostic/foundation only. No web scraping, API calls, credentials, or xG
inference. Source CSV files are never modified in place.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.xg_enrichment import summarize_xg_coverage


@dataclass(frozen=True)
class ManualXGImportResult:
    source_path: str
    output_path: str
    rows_read: int
    rows_valid: int
    rows_invalid: int
    xg_schema: str
    xg_contract_label: str
    xg_production_ready: bool
    validation_errors: list[str]
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(name: Any) -> str:
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {_norm(col): str(col) for col in df.columns}
    for name in names:
        if _norm(name) in by_norm:
            return by_norm[_norm(name)]
    return None


def load_manual_xg_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _match_pair_columns(df: pd.DataFrame) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    return (
        _col(df, "date", "Date"),
        _col(df, "home_team", "HomeTeam"),
        _col(df, "away_team", "AwayTeam"),
        _col(df, "home_xg", "xG_home", "hxg"),
        _col(df, "away_xg", "xG_away", "axg"),
    )


def _optional(df: pd.DataFrame, name: str) -> pd.Series:
    col = _col(df, name)
    if col is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[col]


def normalize_manual_xg_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize safe match-pair manual xG data to standard columns."""
    date, home, away, home_xg, away_xg = _match_pair_columns(df)
    if all([date, home, away, home_xg, away_xg]):
        return pd.DataFrame({
            "date": df[str(date)],
            "home_team": df[str(home)],
            "away_team": df[str(away)],
            "home_xg": pd.to_numeric(df[str(home_xg)], errors="coerce"),
            "away_xg": pd.to_numeric(df[str(away_xg)], errors="coerce"),
            "source_schema": "MATCH_XG_PAIR",
            "source_file": "",
            "xg_source_type": "manual_xg_csv",
            "league": _optional(df, "league"),
            "season": _optional(df, "season"),
        })
    raise ValueError("LONG_XG_PAIRING_REQUIRED")


def validate_manual_xg_dataframe(
    df: pd.DataFrame,
    path: str | Path | None = None,
    *,
    strict: bool = True,
) -> tuple[pd.DataFrame, list[str], list[str], dict[str, Any]]:
    summary = summarize_xg_coverage(df, path=path)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        normalized = normalize_manual_xg_dataframe(df)
    except ValueError:
        normalized = pd.DataFrame()
        errors.append("LONG_XG_PAIRING_REQUIRED")
    if normalized.empty:
        if summary["missing_identity_columns"]:
            errors.append("MISSING_IDENTITY_COLUMNS")
        if summary["missing_xg_columns"]:
            errors.append("MISSING_XG_COLUMNS")
    else:
        null_rows = normalized[["home_xg", "away_xg"]].isna().any(axis=1)
        negative_rows = (normalized[["home_xg", "away_xg"]] < 0).any(axis=1)
        if null_rows.any() and strict:
            errors.append("NULL_XG_VALUES")
        elif null_rows.any():
            warnings.append("NULL_XG_VALUES")
        if negative_rows.any():
            errors.append("NEGATIVE_XG_VALUES")
    if path is not None and ("template" in Path(path).name.lower() or "sample" in Path(path).name.lower()):
        warnings.append("TEMPLATE_OR_DEMO_FILE")
    return normalized, sorted(set(errors)), sorted(set(warnings)), summary


def write_manual_xg_preview(
    df: pd.DataFrame,
    source_path: str | Path,
    output_dir: str | Path = "outputs/xg_import_preview",
) -> Path:
    source = Path(source_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    safe_name = source.name.rsplit(".", 1)[0] + "_manual_xg_preview.csv"
    output = (output_root / safe_name).resolve()
    if output == source.resolve():
        raise ValueError("preview output must not overwrite source file")
    if output_root.resolve() not in output.parents:
        raise ValueError("preview output must stay under output_dir")
    preview = df.copy()
    preview["source_file"] = source.name
    preview.to_csv(output, index=False)
    return output


def import_manual_xg_csv(
    path: str | Path,
    output_dir: str | Path = "outputs/xg_import_preview",
    *,
    strict: bool = True,
    write_preview: bool = True,
) -> ManualXGImportResult:
    df = load_manual_xg_csv(path)
    normalized, errors, warnings, summary = validate_manual_xg_dataframe(df, path=path, strict=strict)
    output_path = ""
    if write_preview and not normalized.empty and not errors:
        output_path = str(write_manual_xg_preview(normalized, path, output_dir=output_dir))
    invalid_mask = pd.Series(False, index=df.index)
    if not normalized.empty:
        invalid_mask = normalized[["home_xg", "away_xg"]].isna().any(axis=1) | (normalized[["home_xg", "away_xg"]] < 0).any(axis=1)
    rows_invalid = int(invalid_mask.sum()) if errors else 0
    rows_read = int(len(df))
    return ManualXGImportResult(
        source_path=str(path),
        output_path=output_path,
        rows_read=rows_read,
        rows_valid=max(0, rows_read - rows_invalid) if not errors else 0,
        rows_invalid=rows_invalid if rows_invalid else (rows_read if errors else 0),
        xg_schema=str(summary.get("xg_schema", "")),
        xg_contract_label=str(summary.get("xg_contract_label", "")),
        xg_production_ready=bool(summary.get("xg_production_ready", False)),
        validation_errors=errors,
        warning_notes=warnings,
    )
