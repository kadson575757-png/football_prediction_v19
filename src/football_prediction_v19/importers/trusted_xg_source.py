# -*- coding: utf-8 -*-
"""Trusted xG source normalization and manual xG fill previews.

Phase 13.1 foundation only. This module copies xG values from user-supplied
trusted CSVs into preview files. It never infers, invents, scrapes, or writes
values back to source/template files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

MATCH_PAIR_SCHEMA = "MATCH_PAIR_XG_SOURCE"
FBREF_LONG_SCHEMA = "FBREF_LONG_XG_SOURCE"
UNDERSTAT_PAIR_SCHEMA = "UNDERSTAT_PAIR_XG_SOURCE"
UNKNOWN_SCHEMA = "UNKNOWN_TRUSTED_XG_SOURCE_SCHEMA"

OUTPUT_COLUMNS = ["date", "home_team", "away_team", "home_xg", "away_xg", "xg_source_file", "xg_source_schema"]


def _norm_col(name: Any) -> str:
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {_norm_col(col): str(col) for col in df.columns}
    for name in names:
        key = _norm_col(name)
        if key in by_norm:
            return by_norm[key]
    return None


def _find_exact_col(df: pd.DataFrame, *names: str) -> str | None:
    existing = {str(col): str(col) for col in df.columns}
    for name in names:
        if name in existing:
            return existing[name]
    return None


def _parse_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=False)
    if parsed.isna().any():
        fallback = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
        parsed = parsed.fillna(fallback)
    return parsed.dt.strftime("%Y-%m-%d")


def _norm_team(value: Any) -> str:
    return " ".join(str(value or "").strip().replace(".", "").split())


def _key(df: pd.DataFrame) -> pd.Series:
    return (
        df["date"].astype(str).str.strip()
        + "|"
        + df["home_team"].astype(str).str.strip().str.lower()
        + "|"
        + df["away_team"].astype(str).str.strip().str.lower()
    )


def detect_trusted_xg_source_schema(df: pd.DataFrame) -> str:
    date = _find_col(df, "date", "Date")
    home = _find_col(df, "home_team", "HomeTeam")
    away = _find_col(df, "away_team", "AwayTeam")
    home_xg = _find_col(df, "home_xg", "xG_home", "hxg")
    away_xg = _find_col(df, "away_xg", "xG_away", "axg")
    understat_home_xg = _find_exact_col(df, "home_xG")
    understat_away_xg = _find_exact_col(df, "away_xG")
    if all([date, home, away, understat_home_xg, understat_away_xg]):
        return UNDERSTAT_PAIR_SCHEMA
    if all([date, home, away, home_xg, away_xg]):
        return MATCH_PAIR_SCHEMA
    fbref_cols = [
        _find_col(df, "Date"),
        _find_col(df, "Squad"),
        _find_col(df, "Opponent"),
        _find_col(df, "xG"),
        _find_col(df, "xGA"),
        _find_col(df, "Venue"),
    ]
    if all(fbref_cols):
        return FBREF_LONG_SCHEMA
    return UNKNOWN_SCHEMA


def _validate_xg_values(out: pd.DataFrame) -> None:
    raw = out[["home_xg", "away_xg"]]
    missing = raw.isna() | raw.astype(str).apply(lambda col: col.str.strip().eq(""))
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    non_numeric = numeric.isna() & ~missing
    if non_numeric.any().any():
        raise ValueError("NON_NUMERIC_XG_VALUES")
    if (numeric < 0).any().any():
        raise ValueError("NEGATIVE_XG_VALUES")
    out["home_xg"] = numeric["home_xg"]
    out["away_xg"] = numeric["away_xg"]


def _normalize_pair(df: pd.DataFrame, schema: str, source_path: str | Path | None) -> pd.DataFrame:
    date = _find_col(df, "date", "Date")
    home = _find_col(df, "home_team", "HomeTeam")
    away = _find_col(df, "away_team", "AwayTeam")
    if schema == UNDERSTAT_PAIR_SCHEMA:
        home_xg = _find_exact_col(df, "home_xG")
        away_xg = _find_exact_col(df, "away_xG")
    else:
        home_xg = _find_col(df, "home_xg", "xG_home", "hxg")
        away_xg = _find_col(df, "away_xg", "xG_away", "axg")
    if not all([date, home, away, home_xg, away_xg]):
        raise ValueError("TRUSTED_XG_SOURCE_SCHEMA_UNSUPPORTED")
    out = pd.DataFrame({
        "date": _parse_date(df[str(date)]),
        "home_team": df[str(home)].map(_norm_team),
        "away_team": df[str(away)].map(_norm_team),
        "home_xg": df[str(home_xg)],
        "away_xg": df[str(away_xg)],
        "xg_source_file": Path(source_path).name if source_path is not None else "",
        "xg_source_schema": schema,
    })
    _validate_xg_values(out)
    return out[OUTPUT_COLUMNS]


def _normalize_fbref_long(df: pd.DataFrame, source_path: str | Path | None) -> pd.DataFrame:
    date = _find_col(df, "Date")
    squad = _find_col(df, "Squad")
    opponent = _find_col(df, "Opponent")
    xg = _find_col(df, "xG")
    xga = _find_col(df, "xGA")
    venue = _find_col(df, "Venue")
    if not all([date, squad, opponent, xg, xga, venue]):
        raise ValueError("TRUSTED_XG_SOURCE_SCHEMA_UNSUPPORTED")
    home_rows = df[df[str(venue)].astype(str).str.strip().str.lower().eq("home")].copy()
    if home_rows.empty:
        raise ValueError("FBREF_HOME_AWAY_PAIRING_AMBIGUOUS")
    out = pd.DataFrame({
        "date": _parse_date(home_rows[str(date)]),
        "home_team": home_rows[str(squad)].map(_norm_team),
        "away_team": home_rows[str(opponent)].map(_norm_team),
        "home_xg": home_rows[str(xg)],
        "away_xg": home_rows[str(xga)],
        "xg_source_file": Path(source_path).name if source_path is not None else "",
        "xg_source_schema": FBREF_LONG_SCHEMA,
    })
    if _key(out).duplicated().any():
        raise ValueError("FBREF_HOME_AWAY_PAIRING_AMBIGUOUS")
    _validate_xg_values(out)
    return out[OUTPUT_COLUMNS]


def normalize_trusted_xg_source(df: pd.DataFrame, source_path: str | Path | None = None) -> pd.DataFrame:
    schema = detect_trusted_xg_source_schema(df)
    if schema in {MATCH_PAIR_SCHEMA, UNDERSTAT_PAIR_SCHEMA}:
        out = _normalize_pair(df, schema, source_path)
    elif schema == FBREF_LONG_SCHEMA:
        out = _normalize_fbref_long(df, source_path)
    else:
        raise ValueError("TRUSTED_XG_SOURCE_SCHEMA_UNSUPPORTED")
    if out[["date", "home_team", "away_team"]].isna().any().any():
        raise ValueError("TRUSTED_XG_SOURCE_MISSING_IDENTITY")
    if _key(out).duplicated().any():
        raise ValueError("TRUSTED_XG_SOURCE_DUPLICATE_KEYS")
    return out


def _normalize_template(template_df: pd.DataFrame) -> pd.DataFrame:
    date = _find_col(template_df, "date", "Date")
    home = _find_col(template_df, "home_team", "HomeTeam", "home")
    away = _find_col(template_df, "away_team", "AwayTeam", "away")
    if not all([date, home, away]):
        raise ValueError("MANUAL_TEMPLATE_MISSING_JOIN_COLUMNS")
    out = template_df.copy()
    out["date"] = _parse_date(out[str(date)])
    out["home_team"] = out[str(home)].map(_norm_team)
    out["away_team"] = out[str(away)].map(_norm_team)
    return out


def join_trusted_xg_to_manual_template(source_df: pd.DataFrame, template_df: pd.DataFrame) -> pd.DataFrame:
    source = normalize_trusted_xg_source(source_df) if "xg_source_schema" not in source_df.columns else source_df.copy()
    template = _normalize_template(template_df)
    source = source.copy()
    template = template.copy()
    source["match_key"] = _key(source)
    template["match_key"] = _key(template)
    source_cols = ["match_key", "home_xg", "away_xg", "xg_source_file", "xg_source_schema"]
    joined = template.drop(columns=[col for col in ["home_xg", "away_xg"] if col in template.columns]).merge(
        source[source_cols],
        on="match_key",
        how="left",
    )
    joined = joined.drop(columns=["match_key"])
    rows_filled = int(joined[["home_xg", "away_xg"]].notna().all(axis=1).sum())
    joined.attrs["rows_template"] = int(len(joined))
    joined.attrs["rows_filled"] = rows_filled
    joined.attrs["rows_missing_xg"] = int(len(joined) - rows_filled)
    joined.attrs["join_coverage_pct"] = round((rows_filled / len(joined) * 100.0), 2) if len(joined) else 0.0
    return joined


def write_filled_manual_xg_preview(
    df: pd.DataFrame,
    source_path: str | Path,
    template_path: str | Path,
    output_dir: str | Path = "outputs/xg_fill_preview",
) -> Path:
    source = Path(source_path)
    template = Path(template_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / f"{source.stem}__to__{template.stem}_filled_manual_xg_preview.csv").resolve()
    if output in {source.resolve(), template.resolve()}:
        raise ValueError("filled manual xG preview must not overwrite source or template")
    if output_root.resolve() not in output.parents:
        raise ValueError("filled manual xG preview must stay under output_dir")
    df.to_csv(output, index=False)
    return output


def build_filled_manual_xg_preview(
    source_path: str | Path,
    template_path: str | Path,
    output_dir: str | Path = "outputs/xg_fill_preview",
    *,
    write_preview: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_df = pd.read_csv(source_path, low_memory=False)
    template_df = pd.read_csv(template_path, low_memory=False)
    normalized = normalize_trusted_xg_source(source_df, source_path=source_path)
    preview = join_trusted_xg_to_manual_template(normalized, template_df)
    output_path = ""
    if write_preview:
        output_path = str(write_filled_manual_xg_preview(preview, source_path, template_path, output_dir=output_dir))
    summary = {
        "rows_template": int(preview.attrs.get("rows_template", len(preview))),
        "rows_filled": int(preview.attrs.get("rows_filled", 0)),
        "rows_missing_xg": int(preview.attrs.get("rows_missing_xg", 0)),
        "join_coverage_pct": float(preview.attrs.get("join_coverage_pct", 0.0)),
        "xg_source_schema": str(normalized["xg_source_schema"].iloc[0]) if not normalized.empty else "",
        "output_path": output_path,
    }
    return preview, summary
