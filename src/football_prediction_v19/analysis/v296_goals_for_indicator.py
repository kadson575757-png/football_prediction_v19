# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context, normalize_match_date
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league


def build_goals_for_indicator(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    match_date: str,
    source_profile: str | None = None,
    cache_only: bool = True,
    enable_network: bool = False,
) -> dict[str, object]:
    del source_profile
    if not competition or not season or not home_team or not away_team or not match_date:
        return _empty("LOW", "competition, season, teams and match_date are required")
    matches = _load_match_rows(
        competition,
        season,
        home_team,
        away_team,
        match_date,
        cache_only=cache_only,
        enable_network=enable_network,
    )
    if matches.empty:
        return _empty("LOW", "No historical football-data rows available before match")
    target_date = normalize_match_date(match_date)
    work = matches.copy()
    work["_date"] = work["match_date"].map(_safe_date)
    work = work[work["_date"].astype(str).lt(target_date)]
    home_totals = _team_goals_for_totals(work, home_team)
    away_totals = _team_goals_for_totals(work, away_team)
    home_n = int(home_totals["matches"])
    away_n = int(away_totals["matches"])
    home_gf = int(home_totals["goals_for"])
    away_gf = int(away_totals["goals_for"])
    home_gfpm = round(float(home_gf / home_n), 4) if home_n else 0.0
    away_gfpm = round(float(away_gf / away_n), 4) if away_n else 0.0
    quality = "FULL" if home_n >= 8 and away_n >= 8 else ("PARTIAL" if home_n >= 3 and away_n >= 3 else "LOW")
    reason = "Goals For per match differential built from matches before match_date" if quality != "LOW" else "Not enough prior matches for both teams"
    return {
        "home_matches_before_match": home_n,
        "away_matches_before_match": away_n,
        "home_goals_for_before_match": home_gf,
        "away_goals_for_before_match": away_gf,
        "home_goals_for_per_match_before_match": home_gfpm,
        "away_goals_for_per_match_before_match": away_gfpm,
        "goals_for_per_match_diff": round(home_gfpm - away_gfpm, 4),
        "goals_for_indicator_quality": quality,
        "goals_for_indicator_reason": reason,
    }


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    out = Path("outputs/v296_goals_for") / _slug(f"{competition}_{season}_{home_team}_vs_{away_team}")
    mapping = resolve_source_league(competition, season, out / "mapping")
    context = build_match_context(home_team, away_team, competition, season, match_date)
    live = run_football_data_live_adapter(
        mapping,
        context,
        out / "football_data",
        enable_network=bool(enable_network and not cache_only),
        cache_dir=Path("outputs/cache/v20_live_sources"),
    )
    path = Path(str(live.get("football_data_live_normalized_path", "")))
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, keep_default_na=False)
    rows = []
    for _, row in frame.iterrows():
        try:
            date = normalize_match_date(str(row.get("Date", "")))
        except Exception:
            continue
        if str(row.get("FTHG", "")).strip() == "" or str(row.get("FTAG", "")).strip() == "":
            continue
        rows.append(
            {
                "match_date": date,
                "home_team": row.get("HomeTeam", ""),
                "away_team": row.get("AwayTeam", ""),
                "home_goals": row.get("FTHG", ""),
                "away_goals": row.get("FTAG", ""),
            }
        )
    return pd.DataFrame(rows)


def _team_goals_for_totals(frame: pd.DataFrame, team: str) -> dict[str, int]:
    team_norm = normalize_team_or_league(team)
    matches = 0
    goals_for = 0
    for _, row in frame.iterrows():
        home_norm = normalize_team_or_league(row.get("home_team", ""))
        away_norm = normalize_team_or_league(row.get("away_team", ""))
        home_goals = int(float(row.get("home_goals", 0)))
        away_goals = int(float(row.get("away_goals", 0)))
        if home_norm == team_norm:
            matches += 1
            goals_for += home_goals
        elif away_norm == team_norm:
            matches += 1
            goals_for += away_goals
    return {"matches": matches, "goals_for": goals_for}


def _safe_date(value: object) -> str:
    try:
        return normalize_match_date(str(value))
    except Exception:
        return ""


def _empty(quality: str, reason: str) -> dict[str, object]:
    return {
        "home_matches_before_match": 0,
        "away_matches_before_match": 0,
        "home_goals_for_before_match": 0,
        "away_goals_for_before_match": 0,
        "home_goals_for_per_match_before_match": 0.0,
        "away_goals_for_per_match_before_match": 0.0,
        "goals_for_per_match_diff": 0.0,
        "goals_for_indicator_quality": quality,
        "goals_for_indicator_reason": reason,
    }


def _slug(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())
