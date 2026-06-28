# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context, normalize_match_date
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league


def resolve_match_result(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    match_date: str,
    source_profile: str | None = None,
    cache_only: bool = True,
    enable_network: bool = False,
    corpus_path: str | Path | None = None,
) -> dict[str, object]:
    del source_profile
    if not competition or not season or not home_team or not away_team or not match_date:
        return _result("DATA_BLOCKED", "", "", "RESULT_UNKNOWN", "none", "competition, season, teams and match_date are required")
    rows = _load_corpus_results(competition, season, corpus_path)
    hit = _match_row(rows, home_team, away_team, match_date)
    if hit is None and enable_network and not cache_only:
        rows = _load_football_data_results(competition, season, home_team, away_team, match_date)
        hit = _match_row(rows, home_team, away_team, match_date)
        source = "football_data"
    else:
        source = "v22_corpus"
    if hit is None:
        reason = "No exact completed result found"
        if not enable_network:
            reason = f"{reason}; network disabled"
        elif cache_only:
            reason = f"{reason}; cache_only prevents live result fallback"
        return _result("NOT_FOUND", "", "", "RESULT_UNKNOWN", source, reason)
    home_goals = _score(hit.get("home_goals", hit.get("FTHG", "")))
    away_goals = _score(hit.get("away_goals", hit.get("FTAG", "")))
    if home_goals == "" or away_goals == "":
        return _result("NOT_FOUND", "", "", "RESULT_UNKNOWN", source, "Fixture found but final score is unavailable")
    return _result("RESOLVED", home_goals, away_goals, _winner_result(int(home_goals), int(away_goals)), source, "Resolved exact completed result")


def _load_corpus_results(competition: str, season: str, corpus_path: str | Path | None) -> pd.DataFrame:
    paths = []
    if corpus_path:
        paths.append(Path(corpus_path))
    paths.append(Path(f"outputs/corpus/v22/{competition.replace(' ', '_')}/{season.replace('/', '-')}/real_season_corpus.csv"))
    paths.append(Path(f"outputs/corpus/v22/{competition.replace(' ', '_')}/{season}/real_season_corpus.csv"))
    for path in paths:
        if path.exists():
            frame = pd.read_csv(path, keep_default_na=False)
            if {"home_team", "away_team", "match_date"}.issubset(frame.columns):
                if "competition" in frame.columns:
                    frame = frame[frame["competition"].astype(str).eq(str(competition))]
                if "season" in frame.columns:
                    frame = frame[frame["season"].astype(str).eq(str(season))]
                return frame
    return pd.DataFrame()


def _load_football_data_results(competition: str, season: str, home_team: str, away_team: str, match_date: str) -> pd.DataFrame:
    out = Path("outputs/v27_result_resolver") / _slug(f"{competition}_{season}_{home_team}_vs_{away_team}")
    mapping = resolve_source_league(competition, season, out / "mapping")
    context = build_match_context(home_team, away_team, competition, season, match_date)
    live = run_football_data_live_adapter(
        mapping,
        context,
        out / "football_data",
        enable_network=True,
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
            date = ""
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


def _match_row(frame: pd.DataFrame, home_team: str, away_team: str, match_date: str) -> pd.Series | None:
    if frame.empty:
        return None
    work = frame.copy()
    work["_date"] = work["match_date"].map(lambda value: _safe_date(value))
    home_norm = normalize_team_or_league(home_team)
    away_norm = normalize_team_or_league(away_team)
    work["_home_norm"] = work["home_team"].map(normalize_team_or_league)
    work["_away_norm"] = work["away_team"].map(normalize_team_or_league)
    hit = work[(work["_date"] == _safe_date(match_date)) & (work["_home_norm"] == home_norm) & (work["_away_norm"] == away_norm)]
    if len(hit) == 1:
        return hit.iloc[0]
    return None


def _safe_date(value: object) -> str:
    try:
        return normalize_match_date(str(value))
    except Exception:
        return ""


def _score(value: object) -> int | str:
    try:
        if str(value).strip() == "":
            return ""
        return int(float(value))
    except (TypeError, ValueError):
        return ""


def _winner_result(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "HOME_WIN"
    if home_goals < away_goals:
        return "AWAY_WIN"
    return "DRAW"


def _result(status: str, home_goals: object, away_goals: object, result: str, source: str, reason: str) -> dict[str, object]:
    return {
        "result_status": status,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": result,
        "source_used": source,
        "reason": reason,
    }


def _slug(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())
