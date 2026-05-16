from __future__ import annotations

from pathlib import Path

import pandas as pd

from .team_names import normalize_team_name

# Alternative column name mappings → canonical names
_TEAM_COL_MAP = {
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "Home": "home_team",
    "Away": "away_team",
}

# Odds column candidates in priority order (first hit wins per odds slot)
_ODDS_CANDIDATES: list[tuple[str, list[str]]] = [
    ("odds_home", ["odds_home", "B365H", "PSH", "MaxH", "AvgH"]),
    ("odds_draw", ["odds_draw", "B365D", "PSD", "MaxD", "AvgD"]),
    ("odds_away", ["odds_away", "B365A", "PSA", "MaxA", "AvgA"]),
]

_OPTIONAL_COLS = ["bookmaker", "market", "updated_at"]


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename alternative column names to canonical names."""
    rename = {}
    cols = set(df.columns)
    for src, dst in _TEAM_COL_MAP.items():
        if src in cols and dst not in cols:
            rename[src] = dst
    if rename:
        df = df.rename(columns=rename)

    # Map odds columns: first candidate present wins
    for canonical, candidates in _ODDS_CANDIDATES:
        if canonical not in df.columns:
            for cand in candidates:
                if cand in df.columns:
                    df = df.rename(columns={cand: canonical})
                    break
    return df


def prepare_odds(
    df: pd.DataFrame,
    input_format: str = "auto",
) -> pd.DataFrame:
    """Prepare a raw odds DataFrame into a clean, normalized form.

    Args:
        df: Raw input DataFrame.
        input_format: "auto" or "native" (only auto/native supported for odds).

    Returns:
        Cleaned DataFrame with columns:
        date, home_team, away_team, odds_home, odds_draw, odds_away
        and any optional columns (bookmaker, market, updated_at) that were present.

    Raises:
        ValueError: on empty input, missing team columns, or no usable odds.
    """
    if df.empty:
        raise ValueError(
            "The odds file is empty. Add at least one odds row before running prepare-odds."
        )

    out = _map_columns(df.copy())

    # Validate team columns
    for col in ("home_team", "away_team"):
        if col not in out.columns:
            raise ValueError(
                f"Required column '{col}' (or an alias like HomeTeam/AwayTeam) is missing "
                "from the odds file. Each odds row must identify the home and away team."
            )

    # Validate at least one odds column exists
    odds_cols_present = [c for c in ("odds_home", "odds_draw", "odds_away") if c in out.columns]
    if not odds_cols_present:
        raise ValueError(
            "No usable odds columns found. Expected odds_home/odds_draw/odds_away "
            "or common aliases like B365H/B365D/B365A, PSH/PSD/PSA, MaxH/MaxD/MaxA."
        )

    # Normalize team names
    out["home_team"] = out["home_team"].apply(normalize_team_name)
    out["away_team"] = out["away_team"].apply(normalize_team_name)

    # Parse dates
    if "date" in out.columns:
        raw_dates = out["date"].astype(str)
        parsed = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")
        still_bad = parsed.isna()
        if still_bad.any():
            parsed[still_bad] = pd.to_datetime(
                raw_dates[still_bad], format="%d/%m/%Y", errors="coerce"
            )
        out["date"] = parsed
    else:
        out["date"] = pd.NaT

    # Convert odds to numeric
    for col in ("odds_home", "odds_draw", "odds_away"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = float("nan")

    # Drop rows where both team names are blank or ALL odds are NaN
    blank_teams = (
        out["home_team"].isna() | (out["home_team"] == "")
        | out["away_team"].isna() | (out["away_team"] == "")
    )
    all_odds_nan = out[["odds_home", "odds_draw", "odds_away"]].isna().all(axis=1)
    out = out[~(blank_teams | all_odds_nan)].reset_index(drop=True)

    if out.empty:
        raise ValueError(
            "All odds rows were dropped because team names were blank or all odds were invalid. "
            "Check that the odds file has valid numeric odds and non-empty team names."
        )

    # Build output columns
    keep = ["date", "home_team", "away_team", "odds_home", "odds_draw", "odds_away"]
    for col in _OPTIONAL_COLS:
        if col in out.columns:
            keep.append(col)

    return out[keep].reset_index(drop=True)


def prepare_odds_file(
    input_path: str,
    output_path: str,
    input_format: str = "auto",
) -> dict[str, object]:
    """Read, prepare, and save an odds CSV file.

    Returns a summary dict with input/output paths and row counts.
    """
    p = Path(input_path)
    if not p.exists():
        raise ValueError(
            f"Odds input file '{input_path}' not found. "
            "Check the path and try again."
        )
    df = pd.read_csv(p)
    out = prepare_odds(df, input_format=input_format)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "rows_in": len(df),
        "rows_out": len(out),
    }


def merge_odds_into_fixtures(
    fixtures: pd.DataFrame,
    odds: pd.DataFrame,
    allow_date_window: int = 0,
    prefer_bookmaker: str | None = None,
) -> tuple[pd.DataFrame, int, int]:
    """Merge odds into fixtures by team names (and optionally date).

    Matching priority:
    1. Exact home_team + away_team + date (when date available in odds)
    2. If allow_date_window > 0: home_team + away_team within ±N days
    3. home_team + away_team without date

    Args:
        fixtures: Prepared fixtures DataFrame (output of prepare-fixtures).
        odds: Cleaned odds DataFrame (output of prepare-odds).
        allow_date_window: Maximum days difference for date-fuzzy matching.
        prefer_bookmaker: If set, prefer rows where bookmaker equals this value.

    Returns:
        (updated_fixtures, matched_count, still_missing_count)
    """
    out = fixtures.copy()
    fx_dates = pd.to_datetime(out["date"], errors="coerce")

    odds_has_dates = odds["date"].notna().any()

    matched = 0
    for i, fx_row in out.iterrows():
        fx_home = fx_row["home_team"]
        fx_away = fx_row["away_team"]
        fx_date = fx_dates.iloc[i]

        # Filter by team names
        mask = (odds["home_team"] == fx_home) & (odds["away_team"] == fx_away)
        candidates = odds[mask]

        if candidates.empty:
            continue

        # Apply date filter
        if odds_has_dates and pd.notna(fx_date):
            odds_dates = pd.to_datetime(candidates["date"], errors="coerce")
            date_diff = (odds_dates - fx_date).dt.days.abs()
            exact = candidates[date_diff == 0]
            if not exact.empty:
                candidates = exact
            elif allow_date_window > 0:
                within = candidates[date_diff <= allow_date_window]
                candidates = within  # empty if none within window
            else:
                candidates = candidates.iloc[0:0]  # no exact match, no window → skip

        # Apply bookmaker preference
        if prefer_bookmaker and "bookmaker" in candidates.columns:
            preferred = candidates[candidates["bookmaker"] == prefer_bookmaker]
            if not preferred.empty:
                candidates = preferred

        if candidates.empty:
            continue

        # Take the first remaining candidate
        best = candidates.iloc[0]
        for col in ("odds_home", "odds_draw", "odds_away"):
            val = best.get(col)
            if pd.notna(val):
                out.at[i, col] = val

        matched += 1

    still_missing = int(out[["odds_home", "odds_draw", "odds_away"]].isna().all(axis=1).sum())
    return out, matched, still_missing


def merge_odds_file(
    fixtures_path: str,
    odds_path: str,
    output_path: str,
    allow_date_window: int = 0,
    prefer_bookmaker: str | None = None,
) -> dict[str, object]:
    """Load fixtures and odds CSVs, merge, and save result."""
    fixtures = pd.read_csv(fixtures_path)
    odds = pd.read_csv(odds_path)
    # Parse odds dates
    if "date" in odds.columns:
        raw = odds["date"].astype(str)
        parsed = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
        bad = parsed.isna()
        if bad.any():
            parsed[bad] = pd.to_datetime(raw[bad], format="%d/%m/%Y", errors="coerce")
        odds = odds.copy()
        odds["date"] = parsed

    updated, matched, still_missing = merge_odds_into_fixtures(
        fixtures, odds,
        allow_date_window=allow_date_window,
        prefer_bookmaker=prefer_bookmaker,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(output, index=False)
    return {
        "output": str(output_path),
        "fixtures_total": len(fixtures),
        "matched": matched,
        "still_missing_odds": still_missing,
    }
