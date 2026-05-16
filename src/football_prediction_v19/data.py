from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

SCORE_PATTERN = re.compile(r"^\s*(\d+)\s*[\-–—]\s*(\d+)\s*$")

STANDARD_RENAMES = {
    "Home": "home_team",
    "Away": "away_team",
    "xG": "home_xg",
    "xG.1": "away_xg",
    "Score": "score",
    "Date": "date",
    "Wk": "matchweek",
    "Venue": "venue",
    "Referee": "referee",
    "Attendance": "attendance",
    "Time": "time",
}

LEAKAGE_COLUMNS = {
    "score", "home_goals", "away_goals", "home_xg", "away_xg", "result",
    "actual_total_goals", "actual_goal_diff"
}


def load_matches(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    out = out.rename(columns={k: v for k, v in STANDARD_RENAMES.items() if k in out.columns})
    # Lowercase common optional columns without destroying original unknown columns.
    lower_map = {}
    for c in out.columns:
        normalized = c.strip().lower().replace(" ", "_")
        if normalized in {
            "odds_home", "odds_draw", "odds_away",
            "odds_home_open", "odds_draw_open", "odds_away_open",
            "formation_home_xg90", "formation_away_xg90",
            "set_piece_xg_ratio_home", "set_piece_xg_ratio_away",
            "fatigue_home", "fatigue_away", "attendance",
        }:
            lower_map[c] = normalized
    out = out.rename(columns=lower_map)
    return out


def parse_score(value: object) -> tuple[float, float]:
    if pd.isna(value):
        return (np.nan, np.nan)
    m = SCORE_PATTERN.match(str(value))
    if not m:
        return (np.nan, np.nan)
    return (float(m.group(1)), float(m.group(2)))


def clean_matches(df: pd.DataFrame, completed_only: bool = True) -> pd.DataFrame:
    """Clean FBref/course-style match data.

    The function keeps the course convention where `xG` is home xG and `xG.1` is away xG,
    but renames them internally to `home_xg` and `away_xg`.
    """
    out = _normalize_columns(df)
    required = ["date", "home_team", "away_team"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    if "matchweek" in out.columns:
        out["matchweek"] = pd.to_numeric(out["matchweek"], errors="coerce")
    else:
        out["matchweek"] = np.nan

    if "score" in out.columns:
        scores = out["score"].apply(parse_score)
        out["home_goals"] = [s[0] for s in scores]
        out["away_goals"] = [s[1] for s in scores]
    else:
        out["score"] = np.nan
        out["home_goals"] = np.nan
        out["away_goals"] = np.nan

    for c in ["home_xg", "away_xg", "attendance"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    for c in ["venue", "referee"]:
        if c not in out.columns:
            out[c] = "Unknown"
        out[c] = out[c].fillna("Unknown").astype(str)

    out["home_team"] = out["home_team"].astype(str).str.strip()
    out["away_team"] = out["away_team"].astype(str).str.strip()
    out["day_name"] = out["date"].dt.day_name().fillna("Unknown")
    out["season_start"] = out["date"].apply(lambda d: int(d.year - 1 if pd.notna(d) and d.month < 8 else d.year) if pd.notna(d) else np.nan)

    out["actual_total_goals"] = out["home_goals"] + out["away_goals"]
    out["actual_goal_diff"] = out["home_goals"] - out["away_goals"]
    out["result"] = np.select(
        [out["home_goals"] > out["away_goals"], out["home_goals"] < out["away_goals"]],
        ["H", "A"],
        default="D",
    )
    out.loc[out["home_goals"].isna() | out["away_goals"].isna(), "result"] = np.nan

    if completed_only:
        subset = ["date", "home_team", "away_team", "home_goals", "away_goals", "home_xg", "away_xg"]
        existing = [c for c in subset if c in out.columns]
        out = out.dropna(subset=existing)

    out = out.sort_values(["date", "matchweek", "home_team", "away_team"]).reset_index(drop=True)
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    blocked = set(LEAKAGE_COLUMNS) | {"date", "time"}
    return [c for c in df.columns if c not in blocked]


def save_dataframe(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)
