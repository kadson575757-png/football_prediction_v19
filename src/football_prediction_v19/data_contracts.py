# -*- coding: utf-8 -*-
"""Input data contracts and data-quality helpers.

Diagnostic/foundation only. This module does not change model probabilities,
recommended-market logic, market-tier rules, betting, staking, or ROI logic.
"""
from __future__ import annotations

import re
import warnings
from typing import Any

import pandas as pd

REQUIRED_MATCH_COLUMNS = (
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
)

OPTIONAL_ODDS_COLUMNS = (
    "B365H",
    "B365D",
    "B365A",
    "odds_home",
    "odds_draw",
    "odds_away",
)

OPTIONAL_XG_COLUMNS = (
    "home_xg",
    "away_xg",
    "xG_home",
    "xG_away",
    "hxg",
    "axg",
)

OPTIONAL_CONTEXT_COLUMNS = (
    "league",
    "season",
    "matchday",
    "venue",
    "home_elo",
    "away_elo",
    "rest_days_home",
    "rest_days_away",
)

QUALITY_LABELS = (
    "READY_FOR_REPLAY",
    "READY_WITH_WARNINGS",
    "MISSING_REQUIRED_COLUMNS",
    "EMPTY_DATA",
    "INVALID_DATA",
)


def normalize_column_name(name: Any) -> str:
    """Return a stable normalized column key for contract matching."""
    return re.sub(r"[^a-z0-9]+", "", str(name or "").strip().lower())


def _available(columns: list[Any], expected: tuple[str, ...]) -> list[str]:
    by_norm = {normalize_column_name(col): str(col) for col in columns}
    found = []
    for col in expected:
        match = by_norm.get(normalize_column_name(col))
        if match is not None:
            found.append(match)
    return found


def detect_column_family(columns: list[Any]) -> dict[str, list[str]]:
    """Detect required and optional column families from a column list."""
    cols = list(columns)
    return {
        "required": _available(cols, REQUIRED_MATCH_COLUMNS),
        "odds": _available(cols, OPTIONAL_ODDS_COLUMNS),
        "xg": _available(cols, OPTIONAL_XG_COLUMNS),
        "context": _available(cols, OPTIONAL_CONTEXT_COLUMNS),
    }


def _col(df: pd.DataFrame, canonical: str) -> str | None:
    norm = normalize_column_name(canonical)
    for col in df.columns:
        if normalize_column_name(col) == norm:
            return str(col)
    return None


def _count_invalid_scores(df: pd.DataFrame) -> int:
    fthg = _col(df, "FTHG")
    ftag = _col(df, "FTAG")
    if not fthg or not ftag:
        return 0
    home = pd.to_numeric(df[fthg], errors="coerce")
    away = pd.to_numeric(df[ftag], errors="coerce")
    return int((home.isna() | away.isna() | (home < 0) | (away < 0)).sum())


def _count_invalid_results(df: pd.DataFrame) -> int:
    ftr = _col(df, "FTR")
    if not ftr:
        return 0
    valid = {"H", "D", "A"}
    invalid = ~df[ftr].astype(str).str.strip().str.upper().isin(valid)
    return int(invalid.sum())


def _count_date_failures(df: pd.DataFrame) -> int:
    date = _col(df, "Date")
    if not date:
        return 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(df[date], errors="coerce")
    return int(parsed.isna().sum())


def _count_blank_teams(df: pd.DataFrame) -> int:
    home = _col(df, "HomeTeam")
    away = _col(df, "AwayTeam")
    if not home or not away:
        return 0
    home_blank = df[home].isna() | df[home].astype(str).str.strip().eq("")
    away_blank = df[away].isna() | df[away].astype(str).str.strip().eq("")
    return int((home_blank | away_blank).sum())


def _count_duplicates(df: pd.DataFrame) -> int:
    keys = [_col(df, col) for col in ("Date", "HomeTeam", "AwayTeam")]
    if any(key is None for key in keys):
        return 0
    return int(df.duplicated(subset=[str(key) for key in keys], keep="first").sum())


def validate_match_dataframe(
    df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Validate a match dataframe against the Phase 12.1 input contract."""
    families = detect_column_family(list(df.columns))
    missing = [
        col for col in REQUIRED_MATCH_COLUMNS
        if normalize_column_name(col) not in {normalize_column_name(x) for x in families["required"]}
    ]
    row_count = int(len(df))
    invalid_score_count = _count_invalid_scores(df)
    invalid_result_count = _count_invalid_results(df)
    date_parse_failure_count = _count_date_failures(df)
    team_name_blank_count = _count_blank_teams(df)
    duplicate_match_count = _count_duplicates(df)

    if row_count == 0:
        quality = "EMPTY_DATA"
    elif missing:
        quality = "MISSING_REQUIRED_COLUMNS"
    elif any((
        invalid_score_count,
        invalid_result_count,
        date_parse_failure_count,
        team_name_blank_count,
    )):
        quality = "INVALID_DATA"
    elif not families["odds"] and not families["xg"]:
        quality = "READY_WITH_WARNINGS"
    else:
        quality = "READY_FOR_REPLAY"

    return {
        "league": league or "",
        "season": season or "",
        "missing_required_columns": missing,
        "available_required_columns": families["required"],
        "available_odds_columns": families["odds"],
        "available_xg_columns": families["xg"],
        "available_context_columns": families["context"],
        "row_count": row_count,
        "duplicate_match_count": duplicate_match_count,
        "invalid_score_count": invalid_score_count,
        "invalid_result_count": invalid_result_count,
        "date_parse_failure_count": date_parse_failure_count,
        "team_name_blank_count": team_name_blank_count,
        "quality_label": quality,
    }


def summarize_data_quality(
    df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Return a CSV/Markdown-friendly data-quality summary."""
    result = validate_match_dataframe(df, league=league, season=season)
    out = result.copy()
    for key in (
        "missing_required_columns",
        "available_required_columns",
        "available_odds_columns",
        "available_xg_columns",
        "available_context_columns",
    ):
        out[key] = " | ".join(result[key])
    return out
