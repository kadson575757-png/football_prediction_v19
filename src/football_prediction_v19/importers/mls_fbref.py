from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..team_names import normalize_team_name

FBREF_MLS_COLUMN_MAP: dict[str, str] = {
    "Date": "date",
    "Home": "home_team",
    "Away": "away_team",
    "Home Team": "home_team",
    "Away Team": "away_team",
    "Score": "score",
    "xG": "home_xg",
    "xG.1": "away_xg",
    "Home xG": "home_xg",
    "Away xG": "away_xg",
    "home_xg": "home_xg",
    "away_xg": "away_xg",
    "Venue": "venue",
    "Referee": "referee",
    "Attendance": "attendance",
    "Comp": "league",
    "Season": "season",
}

OUTPUT_COLUMNS = [
    "date", "season", "league", "home_team", "away_team",
    "score", "home_xg", "away_xg",
    "odds_home", "odds_draw", "odds_away",
    "venue", "referee",
]


def import_mls_fbref(input_path: str | Path, output_path: str | Path | None = None) -> pd.DataFrame:
    """Import FBref-style MLS CSV and normalize to project schema."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}\nProvide a valid FBref-style MLS CSV export.")

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        raise ValueError(f"Could not read CSV file {input_path}: {e}") from e

    if df.empty:
        raise ValueError(f"Input file is empty: {input_path}")

    # Rename columns
    df = df.rename(columns={k: v for k, v in FBREF_MLS_COLUMN_MAP.items() if k in df.columns})
    # Normalize column names (lowercase, strip)
    df.columns = [str(c).strip() for c in df.columns]

    # Check required columns
    for col in ["date", "home_team", "away_team"]:
        if col not in df.columns:
            raise ValueError(
                f"Required column '{col}' (or its FBref alias) not found in {input_path}.\n"
                f"Columns found: {list(df.columns)}"
            )

    # Normalize team names
    df["home_team"] = df["home_team"].astype(str).str.strip().apply(normalize_team_name)
    df["away_team"] = df["away_team"].astype(str).str.strip().apply(normalize_team_name)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=False)
    df = df.dropna(subset=["date", "home_team", "away_team"])

    # Infer league
    if "league" not in df.columns:
        df["league"] = "MLS"
    else:
        df["league"] = df["league"].fillna("MLS").replace("", "MLS")

    # Infer season from date year if missing
    if "season" not in df.columns:
        df["season"] = df["date"].dt.year.astype(str)
    else:
        df["season"] = df["season"].fillna(df["date"].dt.year.astype(str))

    # Convert xG to numeric
    for col in ["home_xg", "away_xg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    # Ensure score column exists
    if "score" not in df.columns:
        df["score"] = np.nan

    # Drop rows missing score (completed match requirement)
    df = df.dropna(subset=["score"])
    df = df[df["score"].astype(str).str.strip() != ""]

    if df.empty:
        raise ValueError("No valid completed match rows found after cleaning. Check that the score column is populated.")

    # Ensure odds columns exist (blank)
    for col in ["odds_home", "odds_draw", "odds_away"]:
        if col not in df.columns:
            df[col] = np.nan

    # Ensure optional columns
    for col in ["venue", "referee"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    # Format date
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    out = df[[c for c in OUTPUT_COLUMNS if c in df.columns]].reset_index(drop=True)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(output_path, index=False)

    return out
