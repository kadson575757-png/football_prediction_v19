# -*- coding: utf-8 -*-
"""Manual xG entry template generator.

Diagnostic/foundation only. This module creates fillable CSV templates and
never infers, invents, or writes xG values back to source data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

XG_ENTRY_TEMPLATE_READY = "XG_ENTRY_TEMPLATE_READY"
XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS = "XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS"
XG_ENTRY_TEMPLATE_EMPTY = "XG_ENTRY_TEMPLATE_EMPTY"
XG_ENTRY_TEMPLATE_INVALID_SOURCE = "XG_ENTRY_TEMPLATE_INVALID_SOURCE"


@dataclass(frozen=True)
class ManualXGTemplateGenerationResult:
    source_path: str
    output_path: str
    rows_source: int
    rows_template: int
    duplicate_keys_removed: int
    missing_identity_rows: int
    template_quality_label: str
    warning_notes: list[str]

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


def _norm_team(value: Any) -> str:
    return " ".join(str(value or "").strip().replace(".", "").split())


def _parse_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=False)
    if parsed.isna().any():
        fallback = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
        parsed = parsed.fillna(fallback)
    return parsed.dt.strftime("%Y-%m-%d")


def normalize_template_source_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize accepted source identity schemas to date/home_team/away_team."""
    out = pd.DataFrame(index=df.index)
    date = _find_col(df, "date", "Date")
    home = _find_col(df, "home_team", "HomeTeam", "home", "Home")
    away = _find_col(df, "away_team", "AwayTeam", "away", "Away")
    if date is not None:
        out["date"] = _parse_date(df[date])
    if home is not None:
        out["home_team"] = df[home].map(_norm_team)
    if away is not None:
        out["away_team"] = df[away].map(_norm_team)
    return out


def _identity_missing_mask(df: pd.DataFrame) -> pd.Series:
    if not {"date", "home_team", "away_team"}.issubset(df.columns):
        return pd.Series([True] * len(df), index=df.index)
    identity = df[["date", "home_team", "away_team"]].copy()
    return identity.isna().any(axis=1) | identity.astype(str).apply(lambda col: col.str.strip().eq("")).any(axis=1)


def extract_xg_entry_rows(
    df: pd.DataFrame,
    source_path: str | Path | None = None,
    league: str | None = None,
    season: str | None = None,
) -> tuple[pd.DataFrame, int, int]:
    normalized = normalize_template_source_dataframe(df)
    if not {"date", "home_team", "away_team"}.issubset(normalized.columns):
        return pd.DataFrame(columns=["date", "home_team", "away_team"]), len(df), 0

    missing_mask = _identity_missing_mask(normalized)
    valid = normalized.loc[~missing_mask, ["date", "home_team", "away_team"]].copy()
    valid["match_key"] = (
        valid["date"].astype(str).str.strip()
        + "|"
        + valid["home_team"].astype(str).str.strip().str.lower()
        + "|"
        + valid["away_team"].astype(str).str.strip().str.lower()
    )
    before = len(valid)
    valid = valid.drop_duplicates("match_key", keep="first").drop(columns=["match_key"])
    duplicate_keys_removed = before - len(valid)
    return valid.reset_index(drop=True), int(missing_mask.sum()), int(duplicate_keys_removed)


def build_manual_xg_entry_template(
    df: pd.DataFrame,
    source_path: str | Path | None = None,
    league: str | None = None,
    season: str | None = None,
) -> tuple[pd.DataFrame, ManualXGTemplateGenerationResult]:
    rows, missing_identity_rows, duplicate_keys_removed = extract_xg_entry_rows(
        df,
        source_path=source_path,
        league=league,
        season=season,
    )
    template = rows.copy()
    if template.empty:
        quality = XG_ENTRY_TEMPLATE_INVALID_SOURCE if len(df) else XG_ENTRY_TEMPLATE_EMPTY
    elif missing_identity_rows or duplicate_keys_removed:
        quality = XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS
    else:
        quality = XG_ENTRY_TEMPLATE_READY

    if not template.empty:
        template["home_xg"] = pd.NA
        template["away_xg"] = pd.NA
        template["league"] = league or ""
        template["season"] = season or ""
        template["source_file"] = Path(source_path).name if source_path is not None else ""
        template["xg_entry_status"] = "NEEDS_MANUAL_ENTRY"
    else:
        template = pd.DataFrame(columns=[
            "date",
            "home_team",
            "away_team",
            "home_xg",
            "away_xg",
            "league",
            "season",
            "source_file",
            "xg_entry_status",
        ])

    warnings: list[str] = []
    if missing_identity_rows:
        warnings.append("MISSING_IDENTITY_ROWS_EXCLUDED")
    if duplicate_keys_removed:
        warnings.append("DUPLICATE_KEYS_REMOVED")
    if quality == XG_ENTRY_TEMPLATE_INVALID_SOURCE:
        warnings.append("MISSING_IDENTITY_COLUMNS")

    result = ManualXGTemplateGenerationResult(
        source_path=str(source_path or ""),
        output_path="",
        rows_source=int(len(df)),
        rows_template=int(len(template)),
        duplicate_keys_removed=int(duplicate_keys_removed),
        missing_identity_rows=int(missing_identity_rows),
        template_quality_label=quality,
        warning_notes=warnings,
    )
    return template, result


def write_manual_xg_entry_template(
    template_df: pd.DataFrame,
    source_path: str | Path,
    output_dir: str | Path = "outputs/xg_entry_templates",
) -> Path:
    source = Path(source_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / f"{source.stem}_manual_xg_entry_template.csv").resolve()
    if output == source.resolve():
        raise ValueError("manual xG entry template must not overwrite source file")
    if output_root.resolve() not in output.parents:
        raise ValueError("manual xG entry template must stay under output_dir")
    template_df.to_csv(output, index=False)
    return output


def generate_manual_xg_entry_template(
    source_path: str | Path,
    output_dir: str | Path = "outputs/xg_entry_templates",
    league: str | None = None,
    season: str | None = None,
    *,
    write_template: bool = True,
) -> ManualXGTemplateGenerationResult:
    df = pd.read_csv(source_path, low_memory=False)
    template, result = build_manual_xg_entry_template(df, source_path=source_path, league=league, season=season)
    output_path = ""
    if write_template:
        output_path = str(write_manual_xg_entry_template(template, source_path, output_dir=output_dir))
    return ManualXGTemplateGenerationResult(**{**result.to_dict(), "output_path": output_path})
