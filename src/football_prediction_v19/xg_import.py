from __future__ import annotations

from pathlib import Path

import pandas as pd

from .team_names import normalize_team_name

# Alternative column name mappings → canonical names
_TEAM_COL_MAP = {
    "Home": "home_team",
    "Away": "away_team",
    "h_team": "home_team",
    "a_team": "away_team",
}

_DATE_COL_MAP = {
    "Date": "date",
}

# xG column candidates in priority order (first hit wins per slot)
_XG_CANDIDATES: list[tuple[str, list[str]]] = [
    ("home_xg", ["home_xg", "home_xG", "xG"]),
    ("away_xg", ["away_xg", "away_xG", "xG.1", "xGA"]),
]

_OPTIONAL_COLS = ["league", "season", "source", "Comp", "Season"]
_OPTIONAL_OUTPUT_COLS = ["league", "season", "source"]


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename alternative column names to canonical names."""
    rename: dict[str, str] = {}
    cols = set(df.columns)

    for src, dst in _TEAM_COL_MAP.items():
        if src in cols and dst not in cols:
            rename[src] = dst

    for src, dst in _DATE_COL_MAP.items():
        if src in cols and dst not in cols:
            rename[src] = dst

    # Map optional descriptive columns
    if "Comp" in cols and "league" not in cols:
        rename["Comp"] = "league"
    if "Season" in cols and "season" not in cols:
        rename["Season"] = "season"

    if rename:
        df = df.rename(columns=rename)

    # Map xG columns: first candidate present wins, skip if canonical already present
    for canonical, candidates in _XG_CANDIDATES:
        if canonical not in df.columns:
            for cand in candidates:
                if cand in df.columns:
                    df = df.rename(columns={cand: canonical})
                    break

    return df


def prepare_xg(
    df: pd.DataFrame,
    input_format: str = "auto",
) -> pd.DataFrame:
    """Prepare a raw xG DataFrame into a clean, normalized form.

    Args:
        df: Raw input DataFrame.
        input_format: "auto", "native", "fbref", or "understat".

    Returns:
        Cleaned DataFrame with columns:
        date, home_team, away_team, home_xg, away_xg
        and any optional columns (league, season, source) that were present.

    Raises:
        ValueError: on empty input, missing team columns, or no usable xG.
    """
    if df.empty:
        raise ValueError(
            "The xG file is empty. Add at least one xG row before running prepare-xg."
        )

    if input_format not in ("auto", "native", "fbref", "understat"):
        raise ValueError(
            f"Unsupported format '{input_format}'. "
            "Use 'auto', 'native', 'fbref', or 'understat'."
        )

    out = _map_columns(df.copy())

    # Validate team columns
    for col in ("home_team", "away_team"):
        if col not in out.columns:
            raise ValueError(
                f"Required column '{col}' (or an alias like Home/Away/h_team/a_team) is missing "
                "from the xG file. Each xG row must identify the home and away team."
            )

    # Validate at least one xG column exists
    xg_cols_present = [c for c in ("home_xg", "away_xg") if c in out.columns]
    if not xg_cols_present:
        raise ValueError(
            "No usable xG columns found. Expected home_xg/away_xg "
            "or common aliases like xG/xG.1 (FBref), xGA (Understat), home_xG/away_xG."
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

    # Convert xG columns to numeric
    for col in ("home_xg", "away_xg"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = float("nan")

    # Drop rows where team names are blank OR both xG values are NaN
    blank_teams = (
        out["home_team"].isna() | (out["home_team"] == "")
        | out["away_team"].isna() | (out["away_team"] == "")
    )
    both_xg_nan = out[["home_xg", "away_xg"]].isna().all(axis=1)
    out = out[~(blank_teams | both_xg_nan)].reset_index(drop=True)

    if out.empty:
        raise ValueError(
            "All xG rows were dropped because team names were blank or all xG values were invalid. "
            "Check that the xG file has valid numeric xG values and non-empty team names."
        )

    # Build output columns
    keep = ["date", "home_team", "away_team", "home_xg", "away_xg"]
    for col in _OPTIONAL_OUTPUT_COLS:
        if col in out.columns:
            keep.append(col)

    return out[keep].reset_index(drop=True)


def prepare_xg_file(
    input_path: str,
    output_path: str,
    input_format: str = "auto",
) -> dict[str, object]:
    """Read, prepare, and save an xG CSV file.

    Returns a summary dict with input/output paths and row counts.
    """
    p = Path(input_path)
    if not p.exists():
        raise ValueError(
            f"xG input file '{input_path}' not found. "
            "Check the path and try again."
        )
    df = pd.read_csv(p)
    out = prepare_xg(df, input_format=input_format)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "rows_in": len(df),
        "rows_out": len(out),
    }


def merge_xg_into_history(
    history: pd.DataFrame,
    xg: pd.DataFrame,
    allow_date_window: int = 0,
    prefer_source: str | None = None,
) -> tuple[pd.DataFrame, int, int]:
    """Merge xG data into historical match data by team names (and optionally date).

    For each matched row:
      history.home_xg  ← xg.home_xg
      history.away_xg  ← xg.away_xg
      history.home_xga ← xg.away_xg  (goals allowed by home = goals scored by away)
      history.away_xga ← xg.home_xg  (goals allowed by away = goals scored by home)

    Matching priority:
    1. Exact home_team + away_team + date (when date available in xg)
    2. If allow_date_window > 0: home_team + away_team within ±N days
    3. home_team + away_team without date

    Args:
        history: Historical matches DataFrame.
        xg: Cleaned xG DataFrame (output of prepare_xg / prepare-xg command).
        allow_date_window: Maximum days difference for date-fuzzy matching.
        prefer_source: If set, prefer rows where source equals this value.

    Returns:
        (updated_history, matched_count, still_missing_count)
    """
    out = history.copy()

    # Ensure xG/xGA columns exist
    for col in ("home_xg", "away_xg", "home_xga", "away_xga"):
        if col not in out.columns:
            out[col] = float("nan")

    hist_dates = pd.to_datetime(out.get("date", pd.Series(dtype="object")), errors="coerce")
    xg_has_dates = xg["date"].notna().any()

    matched = 0
    for i in range(len(out)):
        hist_home = out.at[i, "home_team"] if "home_team" in out.columns else None
        hist_away = out.at[i, "away_team"] if "away_team" in out.columns else None
        hist_date = hist_dates.iloc[i] if i < len(hist_dates) else pd.NaT

        if not hist_home or not hist_away:
            continue

        # Filter by team names
        mask = (xg["home_team"] == hist_home) & (xg["away_team"] == hist_away)
        candidates = xg[mask]

        if candidates.empty:
            continue

        # Apply date filter
        if xg_has_dates and pd.notna(hist_date):
            xg_dates = pd.to_datetime(candidates["date"], errors="coerce")
            date_diff = (xg_dates - hist_date).dt.days.abs()
            exact = candidates[date_diff == 0]
            if not exact.empty:
                candidates = exact
            elif allow_date_window > 0:
                within = candidates[date_diff <= allow_date_window]
                candidates = within
            else:
                candidates = candidates.iloc[0:0]

        if candidates.empty:
            continue

        # Apply source preference
        if prefer_source and "source" in candidates.columns:
            preferred = candidates[candidates["source"] == prefer_source]
            if not preferred.empty:
                candidates = preferred

        best = candidates.iloc[0]
        h_xg = best.get("home_xg")
        a_xg = best.get("away_xg")

        if pd.notna(h_xg):
            out.at[i, "home_xg"] = h_xg
            out.at[i, "away_xga"] = h_xg  # away goals allowed = home scored
        if pd.notna(a_xg):
            out.at[i, "away_xg"] = a_xg
            out.at[i, "home_xga"] = a_xg  # home goals allowed = away scored

        matched += 1

    still_missing = int(out[["home_xg", "away_xg"]].isna().all(axis=1).sum())
    return out, matched, still_missing


def merge_xg_file(
    history_path: str,
    xg_path: str,
    output_path: str,
    allow_date_window: int = 0,
    prefer_source: str | None = None,
) -> dict[str, object]:
    """Load history and xG CSVs, merge, and save result."""
    history = pd.read_csv(history_path)
    xg = pd.read_csv(xg_path)

    # Parse xG dates
    if "date" in xg.columns:
        raw = xg["date"].astype(str)
        parsed = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
        bad = parsed.isna()
        if bad.any():
            parsed[bad] = pd.to_datetime(raw[bad], format="%d/%m/%Y", errors="coerce")
        xg = xg.copy()
        xg["date"] = parsed

    updated, matched, still_missing = merge_xg_into_history(
        history, xg,
        allow_date_window=allow_date_window,
        prefer_source=prefer_source,
    )

    # When both FBref-alias columns (xG/xG.1) and canonical columns (home_xg/away_xg) exist,
    # fill any still-NaN canonical values from the aliases, then drop the aliases.
    # This prevents duplicate-column errors when downstream code tries to rename them again.
    if "home_xg" in updated.columns and "xG" in updated.columns:
        still_nan = updated["home_xg"].isna()
        updated.loc[still_nan, "home_xg"] = updated.loc[still_nan, "xG"]
        updated = updated.drop(columns=["xG"])
    if "away_xg" in updated.columns and "xG.1" in updated.columns:
        still_nan = updated["away_xg"].isna()
        updated.loc[still_nan, "away_xg"] = updated.loc[still_nan, "xG.1"]
        updated = updated.drop(columns=["xG.1"])

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(output, index=False)
    return {
        "output": str(output_path),
        "history_total": len(history),
        "matched": matched,
        "still_missing_xg": still_missing,
    }
