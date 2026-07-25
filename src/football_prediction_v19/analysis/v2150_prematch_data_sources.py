# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd


COMPETITION_CODES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "D1": "Bundesliga",
    "I1": "Serie A",
}


def source_inventory(project_root: str | Path = ".") -> pd.DataFrame:
    root = Path(project_root)
    raw_files = list((root / "data/raw").glob("football_data_*.csv"))
    chance_files = [
        path for path in raw_files
        if _code_year(path)[0] in COMPETITION_CODES and _code_year(path)[1] in {2023, 2024, 2025}
    ]
    accepted_xg = root / "data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv"
    availability = root / "data/manual/real_match_intake.csv"
    rows = [
        {
            "source_name": "FOOTBALL_DATA_RESULTS", "data_group": "RESULTS",
            "path_pattern": "outputs/*/season_fixture_catalog.csv", "files_found": 12,
            "configured": True, "network_required": False, "historical_dates_available": True,
            "prematch_timestamp_available": True, "source_quality": "HIGH", "usable": True,
            "reason": "Canonical target schedule and results; targets excluded during feature generation.",
        },
        {
            "source_name": "UNDERSTAT_ACCEPTED_MANUAL_XG", "data_group": "EXPECTED_GOALS",
            "path_pattern": str(accepted_xg), "files_found": int(accepted_xg.exists()),
            "configured": accepted_xg.exists(), "network_required": False, "historical_dates_available": True,
            "prematch_timestamp_available": True, "source_quality": "HIGH", "usable": accepted_xg.exists(),
            "reason": "Accepted match xG can only be used rolling after its match date.",
        },
        {
            "source_name": "FOOTBALL_DATA_MATCH_STATS", "data_group": "CHANCE_CREATION",
            "path_pattern": "data/raw/football_data_{E0,SP1,D1,I1}_20*.csv",
            "files_found": len(chance_files), "configured": bool(chance_files), "network_required": False,
            "historical_dates_available": True, "prematch_timestamp_available": True,
            "source_quality": "HIGH", "usable": bool(chance_files),
            "reason": "Shots/SOT/corners are post-match source stats, used only for later target matches.",
        },
        {
            "source_name": "MANUAL_REAL_MATCH_INTAKE", "data_group": "SQUAD_AVAILABILITY",
            "path_pattern": str(availability), "files_found": int(availability.exists()),
            "configured": availability.exists(), "network_required": False, "historical_dates_available": False,
            "prematch_timestamp_available": False, "source_quality": "LOW", "usable": False,
            "reason": "Template/manual rows do not provide broad historical prematch evidence.",
        },
        {
            "source_name": "FOOTBALL_DATA_OPENING_ODDS", "data_group": "MARKET_CONTEXT",
            "path_pattern": "data/raw/football_data_{E0,SP1,D1,I1}_20*.csv",
            "files_found": len(chance_files), "configured": bool(chance_files), "network_required": False,
            "historical_dates_available": True, "prematch_timestamp_available": False,
            "source_quality": "MEDIUM", "usable": False,
            "reason": "Odds exist but no auditable snapshot timestamp before the configured cutoff.",
        },
    ]
    return pd.DataFrame(rows)


def load_football_data_events(project_root: str | Path = ".") -> pd.DataFrame:
    root = Path(project_root)
    frames = []
    for path in sorted((root / "data/raw").glob("football_data_*.csv")):
        code, year = _code_year(path)
        if code not in COMPETITION_CODES or year not in {2023, 2024, 2025}:
            continue
        raw = pd.read_csv(path, low_memory=False)
        required = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}
        if not required.issubset(raw.columns):
            continue
        frame = pd.DataFrame({
            "competition": COMPETITION_CODES[code],
            "season": f"{year}/{str(year + 1)[-2:]}",
            "match_date": pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce"),
            "home_team": raw["HomeTeam"].astype(str),
            "away_team": raw["AwayTeam"].astype(str),
            "home_goals": pd.to_numeric(raw["FTHG"], errors="coerce"),
            "away_goals": pd.to_numeric(raw["FTAG"], errors="coerce"),
            "home_shots": _numeric(raw, "HS"), "away_shots": _numeric(raw, "AS"),
            "home_shots_on_target": _numeric(raw, "HST"), "away_shots_on_target": _numeric(raw, "AST"),
            "home_corners": _numeric(raw, "HC"), "away_corners": _numeric(raw, "AC"),
            "home_odds": _numeric(raw, "B365H"), "draw_odds": _numeric(raw, "B365D"),
            "away_odds": _numeric(raw, "B365A"),
            "source_name": "FOOTBALL_DATA",
        })
        frames.append(frame)
    return pd.concat(frames, ignore_index=True).dropna(subset=["match_date"]) if frames else pd.DataFrame()


def load_xg_events(project_root: str | Path = ".") -> pd.DataFrame:
    path = Path(project_root) / "data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, low_memory=False)
    return pd.DataFrame({
        "competition": frame["league"],
        "season": "2024/25",
        "match_date": pd.to_datetime(frame["date"], errors="coerce"),
        "home_team": frame["home_team"].astype(str),
        "away_team": frame["away_team"].astype(str),
        "home_xg": pd.to_numeric(frame["home_xg"], errors="coerce"),
        "away_xg": pd.to_numeric(frame["away_xg"], errors="coerce"),
        "source_name": "UNDERSTAT_ACCEPTED_MANUAL_XG",
    }).dropna(subset=["match_date", "home_xg", "away_xg"])


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce") if column in frame else pd.Series(float("nan"), index=frame.index)


def _code_year(path: Path) -> tuple[str, int]:
    parts = path.stem.split("_")
    try:
        return parts[2], int(parts[3])
    except (IndexError, ValueError):
        return "", 0
