from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from .team_names import normalize_team_name

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

REAL_MATCH_REQUIRED_COLUMNS = [
    "date",
    "season",
    "league",
    "home_team",
    "away_team",
    "score",
    "home_xg",
    "away_xg",
    "odds_home",
    "odds_draw",
    "odds_away",
    "venue",
    "referee",
]

REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS = [
    "home_xga",
    "away_xga",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_big_chances",
    "away_big_chances",
    "home_possession",
    "away_possession",
    "home_ppda",
    "away_ppda",
    "home_rest_days",
    "away_rest_days",
    "home_injuries_count",
    "away_injuries_count",
    "home_market_value",
    "away_market_value",
]

SUPPORTED_REAL_MATCH_FORMATS = {"auto", "native", "fbref", "football-data"}

FBREF_RENAMES = {
    "Date": "date",
    "Season": "season",
    "Comp": "league",
    "Home": "home_team",
    "Away": "away_team",
    "Score": "score",
    "xG": "home_xg",
    "xG.1": "away_xg",
    "Venue": "venue",
    "Referee": "referee",
}

FOOTBALL_DATA_RENAMES = {
    "Date": "date",
    "Div": "league",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "home_goals",
    "FTAG": "away_goals",
    "FTR": "result",
    "B365H": "odds_home",
    "B365D": "odds_draw",
    "B365A": "odds_away",
}

_DIV_TO_LEAGUE: dict[str, str] = {
    "E0": "Premier League",
    "E1": "Championship",
    "E2": "League One",
    "E3": "League Two",
    "D1": "Bundesliga",
    "D2": "2. Bundesliga",
    "SP1": "La Liga",
    "SP2": "Segunda Division",
    "I1": "Serie A",
    "I2": "Serie B",
    "F1": "Ligue 1",
    "F2": "Ligue 2",
    "N1": "Eredivisie",
    "B1": "Pro League",
    "P1": "Primeira Liga",
    "T1": "Super Lig",
    "G1": "Super League Greece",
    "SC0": "Scottish Premiership",
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
            *REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS,
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


def _score_from_goals(home_goals: object, away_goals: object) -> str:
    if pd.isna(home_goals) or pd.isna(away_goals):
        return ""
    return f"{int(float(home_goals))}-{int(float(away_goals))}"


def _normalize_native_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


def _detect_real_match_format(df: pd.DataFrame) -> str:
    columns = set(str(c).strip() for c in df.columns)
    normalized = {c.lower().replace(" ", "_") for c in columns}
    if {"HomeTeam", "AwayTeam", "FTHG", "FTAG"}.issubset(columns):
        return "football-data"
    if {"Home", "Away", "Score", "xG", "xG.1"}.issubset(columns):
        return "fbref"
    if {"date", "home_team", "away_team"}.issubset(normalized):
        return "native"
    raise ValueError("Could not auto-detect input format. Use --format native, fbref, or football-data.")


def _coerce_real_match_format(df: pd.DataFrame, input_format: str) -> pd.DataFrame:
    if input_format not in SUPPORTED_REAL_MATCH_FORMATS:
        allowed = ", ".join(sorted(SUPPORTED_REAL_MATCH_FORMATS))
        raise ValueError(f"Unsupported format: {input_format}. Allowed values: {allowed}")
    selected = _detect_real_match_format(df) if input_format == "auto" else input_format
    if selected == "native":
        out = _normalize_native_columns(df)
    elif selected == "fbref":
        out = _normalize_native_columns(df.rename(columns=FBREF_RENAMES))
        for col in ["odds_home", "odds_draw", "odds_away"]:
            if col not in out.columns:
                out[col] = np.nan
    else:
        out = _normalize_native_columns(df.rename(columns=FOOTBALL_DATA_RENAMES))
        if "score" not in out.columns and {"home_goals", "away_goals"}.issubset(out.columns):
            out["score"] = [_score_from_goals(h, a) for h, a in zip(out["home_goals"], out["away_goals"])]
        if "season" not in out.columns:
            parsed_dates = pd.to_datetime(out.get("date"), errors="coerce", dayfirst=True)
            out["season"] = parsed_dates.apply(
                lambda d: f"{d.year - 1}-{d.year}" if pd.notna(d) and d.month < 8 else (f"{d.year}-{d.year + 1}" if pd.notna(d) else "Unknown")
            )
        if "league" in out.columns:
            out["league"] = out["league"].map(lambda v: _DIV_TO_LEAGUE.get(str(v).strip(), str(v).strip()) if pd.notna(v) and str(v).strip() not in ("", "nan") else "Unknown")
        else:
            out["league"] = "Unknown"
        if "venue" not in out.columns:
            out["venue"] = "Unknown"
        if "referee" not in out.columns:
            out["referee"] = "Unknown"
        if "home_xg" not in out.columns:
            out["home_xg"] = np.nan
        if "away_xg" not in out.columns:
            out["away_xg"] = np.nan
    out.attrs["detected_format"] = selected
    return out


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

    raw_dates = out["date"].copy()
    out["date"] = pd.to_datetime(raw_dates, errors="coerce")
    if out["date"].isna().any():
        reparsed = pd.to_datetime(raw_dates, errors="coerce", dayfirst=True)
        out["date"] = out["date"].fillna(reparsed)
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

    for c in ["home_xg", "away_xg", "attendance", *REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    for c in ["venue", "referee"]:
        if c not in out.columns:
            out[c] = "Unknown"
        out[c] = out[c].fillna("Unknown").astype(str)

    out["home_team"] = out["home_team"].astype(str).str.strip()
    out["away_team"] = out["away_team"].astype(str).str.strip()
    out["day_name"] = out["date"].dt.day_name().fillna("Unknown")
    # Compute European season_start (Aug-Jul seasons: Jan-Jul map to year-1)
    euro_season_start = out["date"].apply(
        lambda d: int(d.year - 1 if pd.notna(d) and d.month < 8 else d.year) if pd.notna(d) else np.nan
    )
    # MLS uses calendar-year seasons (Feb-Nov): season_start always equals the calendar year
    if "league" in out.columns:
        is_mls = out["league"].astype(str).str.strip() == "MLS"
        out["season_start"] = euro_season_start.where(~is_mls, out["date"].dt.year)
        # Preserve NaN for rows where date is NaT
        out.loc[out["date"].isna(), "season_start"] = np.nan
    else:
        out["season_start"] = euro_season_start

    out["actual_total_goals"] = out["home_goals"] + out["away_goals"]
    out["actual_goal_diff"] = out["home_goals"] - out["away_goals"]
    out["result"] = np.select(
        [out["home_goals"] > out["away_goals"], out["home_goals"] < out["away_goals"]],
        ["H", "A"],
        default="D",
    )
    out.loc[out["home_goals"].isna() | out["away_goals"].isna(), "result"] = np.nan

    if completed_only:
        subset = ["date", "home_team", "away_team", "home_goals", "away_goals"]
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


def prepare_real_matches(df: pd.DataFrame, input_format: str = "auto") -> pd.DataFrame:
    """Prepare user-supplied historical match data for model training."""
    out = _coerce_real_match_format(df, input_format)
    detected_format = out.attrs["detected_format"]
    missing = [col for col in REAL_MATCH_REQUIRED_COLUMNS if col not in out.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    optional_found = [col for col in REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS if col in out.columns]
    optional_missing = [col for col in REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS if col not in out.columns]
    out = out[REAL_MATCH_REQUIRED_COLUMNS + optional_found].copy()
    rows_before = len(out)
    raw_dates = out["date"].copy()
    out["date"] = pd.to_datetime(raw_dates, errors="coerce", dayfirst=detected_format == "football-data")
    if out["date"].isna().any():
        reparsed = pd.to_datetime(raw_dates, errors="coerce", dayfirst=True)
        out["date"] = out["date"].fillna(reparsed)
    scores = out["score"].apply(parse_score)
    out["home_goals"] = [score[0] for score in scores]
    out["away_goals"] = [score[1] for score in scores]

    for col in ["home_xg", "away_xg", "odds_home", "odds_draw", "odds_away", *optional_found]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in ["season", "league", "home_team", "away_team", "venue", "referee"]:
        out[col] = out[col].fillna("Unknown").astype(str).str.strip()
    out["home_team"] = out["home_team"].apply(normalize_team_name)
    out["away_team"] = out["away_team"].apply(normalize_team_name)

    out = out.dropna(subset=["date", "score", "home_goals", "away_goals"])
    out = out.sort_values(["date", "league", "home_team", "away_team"]).reset_index(drop=True)
    out.attrs["rows_before"] = rows_before
    out.attrs["rows_after"] = len(out)
    out.attrs["rows_dropped"] = rows_before - len(out)
    out.attrs["optional_found"] = optional_found
    out.attrs["optional_missing"] = optional_missing
    out.attrs["detected_format"] = detected_format
    return out


def prepare_real_matches_file(input_path: str | Path, output_path: str | Path, input_format: str = "auto") -> dict[str, int | str]:
    raw = load_matches(input_path)
    clean = prepare_real_matches(raw, input_format=input_format)
    save_dataframe(clean, output_path)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "format": str(clean.attrs["detected_format"]),
        "rows_read": int(clean.attrs["rows_before"]),
        "rows_written": int(clean.attrs["rows_after"]),
        "rows_dropped": int(clean.attrs["rows_dropped"]),
        "optional_found": ", ".join(clean.attrs["optional_found"]) or "none",
        "optional_missing": ", ".join(clean.attrs["optional_missing"]) or "none",
    }
