from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..team_names import normalize_team_name

# Column alias maps - maps possible input column names to canonical output names
DATE_ALIASES = ["date", "Date", "match_date", "Match Date", "MatchDate"]
HOME_TEAM_ALIASES = ["home_team", "Home", "Home Team", "HomeTeam", "home"]
AWAY_TEAM_ALIASES = ["away_team", "Away", "Away Team", "AwayTeam", "away"]
ODDS_HOME_ALIASES = ["odds_home", "Home Odds", "HomeOdds", "1", "home_odds", "H", "home_win", "Home Win"]
ODDS_DRAW_ALIASES = ["odds_draw", "Draw Odds", "DrawOdds", "X", "draw_odds", "D", "Draw"]
ODDS_AWAY_ALIASES = ["odds_away", "Away Odds", "AwayOdds", "2", "away_odds", "A", "Away Win"]
BOOKMAKER_ALIASES = ["bookmaker", "Bookmaker", "bookie", "source", "Source"]
MARKET_ALIASES = ["market", "Market", "bet_type", "BetType"]
UPDATED_AT_ALIASES = ["updated_at", "Closing Time", "timestamp", "UpdatedAt", "closing_time", "date_updated"]

OUTPUT_COLUMNS = [
    "date", "home_team", "away_team",
    "odds_home", "odds_draw", "odds_away",
    "bookmaker", "market", "updated_at",
]


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """Find the first matching column name from a list of aliases."""
    for alias in aliases:
        if alias in df.columns:
            return alias
    # Case-insensitive fallback
    lower_cols = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in lower_cols:
            return lower_cols[alias.lower()]
    return None


def import_historical_odds(
    input_path: str | Path,
    output_path: str | Path | None = None,
    league: str = "MLS",
) -> pd.DataFrame:
    """Import historical odds CSV with flexible column names and normalize to project schema."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Odds file not found: {input_path}\n"
            f"Provide a CSV with columns like: date, home_team, away_team, odds_home, odds_draw, odds_away"
        )

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        raise ValueError(f"Could not read CSV file {input_path}: {e}") from e

    if df.empty:
        raise ValueError(f"Odds file is empty: {input_path}")

    # Map columns
    col_map: dict[str, str] = {}
    rename: dict[str, str] = {}

    date_col = _find_column(df, DATE_ALIASES)
    if date_col is None:
        raise ValueError(
            f"No date column found in {input_path}.\n"
            f"Columns found: {list(df.columns)}\n"
            f"Expected one of: {DATE_ALIASES}"
        )
    rename[date_col] = "date"

    home_col = _find_column(df, HOME_TEAM_ALIASES)
    if home_col is None:
        raise ValueError(
            f"No home team column found in {input_path}.\n"
            f"Columns found: {list(df.columns)}\n"
            f"Expected one of: {HOME_TEAM_ALIASES}"
        )
    rename[home_col] = "home_team"

    away_col = _find_column(df, AWAY_TEAM_ALIASES)
    if away_col is None:
        raise ValueError(
            f"No away team column found in {input_path}.\n"
            f"Columns found: {list(df.columns)}\n"
            f"Expected one of: {AWAY_TEAM_ALIASES}"
        )
    rename[away_col] = "away_team"

    odds_home_col = _find_column(df, ODDS_HOME_ALIASES)
    odds_draw_col = _find_column(df, ODDS_DRAW_ALIASES)
    odds_away_col = _find_column(df, ODDS_AWAY_ALIASES)

    if odds_home_col is None or odds_away_col is None:
        raise ValueError(
            f"No odds columns found in {input_path}.\n"
            f"Columns found: {list(df.columns)}\n"
            f"Need at minimum: home odds and away odds.\n"
            f"Expected home odds column to be one of: {ODDS_HOME_ALIASES}\n"
            f"Expected away odds column to be one of: {ODDS_AWAY_ALIASES}"
        )
    rename[odds_home_col] = "odds_home"
    if odds_draw_col:
        rename[odds_draw_col] = "odds_draw"
    if odds_away_col:
        rename[odds_away_col] = "odds_away"

    # Optional columns
    bm_col = _find_column(df, BOOKMAKER_ALIASES)
    if bm_col:
        rename[bm_col] = "bookmaker"
    mkt_col = _find_column(df, MARKET_ALIASES)
    if mkt_col:
        rename[mkt_col] = "market"
    upd_col = _find_column(df, UPDATED_AT_ALIASES)
    if upd_col:
        rename[upd_col] = "updated_at"

    df = df.rename(columns=rename)

    # Normalize team names
    df["home_team"] = df["home_team"].astype(str).str.strip().apply(normalize_team_name)
    df["away_team"] = df["away_team"].astype(str).str.strip().apply(normalize_team_name)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=False)
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    # Convert odds to numeric
    for col in ["odds_home", "odds_draw", "odds_away"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    # Fill optional columns
    for col in ["bookmaker", "market", "updated_at"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    if "market" in df.columns and (df["market"] == "").all():
        df["market"] = "h2h"

    out = df[[c for c in OUTPUT_COLUMNS if c in df.columns]].reset_index(drop=True)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(output_path, index=False)

    return out


def merge_historical_odds(
    matches_path: str | Path,
    odds_path: str | Path,
    output_path: str | Path | None = None,
    date_window: int = 2,
    overwrite: bool = False,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Merge historical odds into a matches DataFrame by date+team matching.

    Returns (merged_df, stats_dict).
    """
    matches_path = Path(matches_path)
    odds_path = Path(odds_path)

    if not matches_path.exists():
        raise FileNotFoundError(f"Matches file not found: {matches_path}")
    if not odds_path.exists():
        raise FileNotFoundError(f"Odds file not found: {odds_path}")

    matches = pd.read_csv(matches_path)
    odds = pd.read_csv(odds_path)

    matches["_date"] = pd.to_datetime(matches["date"], errors="coerce")
    odds["_date"] = pd.to_datetime(odds["date"], errors="coerce")

    # Normalize team names in matches too (in case they weren't normalized yet)
    matches["_home"] = matches["home_team"].astype(str).apply(normalize_team_name)
    matches["_away"] = matches["away_team"].astype(str).apply(normalize_team_name)
    odds["_home"] = odds["home_team"].astype(str).apply(normalize_team_name)
    odds["_away"] = odds["away_team"].astype(str).apply(normalize_team_name)

    # Ensure odds columns exist in matches
    for col in ["odds_home", "odds_draw", "odds_away"]:
        if col not in matches.columns:
            matches[col] = np.nan
        matches[col] = pd.to_numeric(matches[col], errors="coerce")

    matched = 0
    skipped_non_null = 0

    for i, odds_row in odds.iterrows():
        if pd.isna(odds_row["_date"]):
            continue
        # Find match rows within date window
        date_diff = (matches["_date"] - odds_row["_date"]).abs()
        team_match = (matches["_home"] == odds_row["_home"]) & (matches["_away"] == odds_row["_away"])
        within_window = date_diff <= pd.Timedelta(days=date_window)
        candidates = matches[team_match & within_window]

        if candidates.empty:
            continue

        for idx in candidates.index:
            has_odds = (
                pd.notna(matches.at[idx, "odds_home"]) or
                pd.notna(matches.at[idx, "odds_draw"]) or
                pd.notna(matches.at[idx, "odds_away"])
            )
            if has_odds and not overwrite:
                skipped_non_null += 1
                continue
            matches.at[idx, "odds_home"] = odds_row.get("odds_home", np.nan)
            matches.at[idx, "odds_draw"] = odds_row.get("odds_draw", np.nan)
            matches.at[idx, "odds_away"] = odds_row.get("odds_away", np.nan)
            matched += 1

    # Drop helper columns
    matches = matches.drop(columns=["_date", "_home", "_away"])

    missing_after = matches["odds_home"].isna().sum()
    total = len(matches)

    stats = {
        "total_matches": total,
        "matched": matched,
        "unmatched": total - matched - skipped_non_null,
        "skipped_non_null": skipped_non_null,
        "missing_odds_after": missing_after,
    }

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        matches.to_csv(output_path, index=False)

    return matches, stats
