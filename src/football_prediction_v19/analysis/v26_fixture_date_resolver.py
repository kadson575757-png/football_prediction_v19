# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context, normalize_match_date
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


def resolve_fixture_date(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    source_profile: str | None = None,
    cache_only: bool = True,
    enable_network: bool = False,
    corpus_path: str | Path | None = None,
    allow_team_alias: bool = True,
) -> dict[str, object]:
    if not competition or not season or not home_team or not away_team:
        return _result("DATA_BLOCKED", competition, season, home_team, away_team, "", [], "competition, season, home and away are required")
    corpus = _load_corpus(competition, season, corpus_path)
    if corpus.empty:
        if enable_network and not cache_only:
            football_data = _load_football_data_live_candidates(
                competition,
                season,
                home_team,
                away_team,
                source_profile=source_profile,
                allow_team_alias=allow_team_alias,
            )
            if not football_data.empty:
                return _resolve_from_frame(
                    football_data,
                    competition,
                    season,
                    home_team,
                    away_team,
                    allow_team_alias=allow_team_alias,
                    source_used="football_data",
                    reason_prefix="Resolved exact home/away fixture from football-data live source",
                )
        reason = "No v22 corpus/cache fixture rows found"
        if not enable_network:
            reason = f"{reason}; network fallback disabled"
        elif cache_only:
            reason = f"{reason}; cache_only prevents live football-data fallback"
        else:
            reason = f"{reason}; football-data fallback returned no usable fixture rows"
        return _result("NOT_FOUND", competition, season, home_team, away_team, "", [], reason)
    return _resolve_from_frame(
        corpus,
        competition,
        season,
        home_team,
        away_team,
        allow_team_alias=allow_team_alias,
        source_used="v22_corpus",
        reason_prefix="Resolved exact home/away fixture from corpus",
    )


def _resolve_from_frame(
    frame: pd.DataFrame,
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    *,
    allow_team_alias: bool,
    source_used: str,
    reason_prefix: str,
) -> dict[str, object]:
    home_norm = normalize_team_or_league(home_team) if allow_team_alias else str(home_team).strip().lower()
    away_norm = normalize_team_or_league(away_team) if allow_team_alias else str(away_team).strip().lower()
    work = frame.copy()
    work["_home_norm"] = work["home_team"].map(normalize_team_or_league)
    work["_away_norm"] = work["away_team"].map(normalize_team_or_league)
    exact = work[(work["_home_norm"] == home_norm) & (work["_away_norm"] == away_norm)]
    reversed_rows = work[(work["_home_norm"] == away_norm) & (work["_away_norm"] == home_norm)]
    if len(exact) == 1:
        row = exact.iloc[0]
        return {
            **_result("RESOLVED", competition, season, home_team, away_team, str(row.get("match_date", "")), exact, reason_prefix),
            "canonical_home_team": row.get("home_team", home_team),
            "canonical_away_team": row.get("away_team", away_team),
            "source_used": source_used,
            "confidence": 1.0,
            "reversed_fixture_found": bool(len(reversed_rows) > 0),
            "alias_matched": bool(home_norm != str(home_team).strip().lower() or away_norm != str(away_team).strip().lower()),
        }
    if len(exact) > 1:
        return {**_result("AMBIGUOUS", competition, season, home_team, away_team, "", exact, "Multiple exact home/away fixture candidates found"), "source_used": source_used, "reversed_fixture_found": bool(len(reversed_rows) > 0), "alias_matched": False}
    if len(reversed_rows) > 0:
        return {**_result("NOT_FOUND", competition, season, home_team, away_team, "", [], "Only reversed fixture was found; home/away was not guessed"), "source_used": source_used, "reversed_fixture_found": True, "candidates": _candidates(reversed_rows), "candidates_count": 0}
    return {**_result("NOT_FOUND", competition, season, home_team, away_team, "", [], "No exact home/away fixture found"), "source_used": source_used}


def _load_corpus(competition: str, season: str, corpus_path: str | Path | None) -> pd.DataFrame:
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


def _load_football_data_live_candidates(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    *,
    source_profile: str | None,
    allow_team_alias: bool,
) -> pd.DataFrame:
    del source_profile, allow_team_alias
    out = Path("outputs/fixture_resolver/v26") / _slug(f"{competition}_{season}_{home_team}_vs_{away_team}")
    mapping = resolve_source_league(competition, season, out / "mapping")
    context = build_match_context(
        home_team,
        away_team,
        competition,
        season,
        _season_anchor_date(season),
    )
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
    normalized = pd.read_csv(path, keep_default_na=False)
    return _football_data_to_fixture_frame(normalized, competition, season)


def _football_data_to_fixture_frame(df: pd.DataFrame, competition: str, season: str) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        try:
            date = normalize_match_date(str(row.get("Date", "")))
        except Exception:
            date = ""
        if not date:
            continue
        rows.append(
            {
                "competition": competition,
                "season": season,
                "match_date": date,
                "home_team": row.get("HomeTeam", ""),
                "away_team": row.get("AwayTeam", ""),
                "football_data_available": True,
                "result_1x2": row.get("FTR", ""),
                "can_backtest": str(row.get("FTR", "")).strip() in {"H", "D", "A"},
            }
        )
    return pd.DataFrame(rows)


def _season_anchor_date(season: str) -> str:
    text = str(season)
    for token in text.replace("/", " ").replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            return f"{token}-08-01"
    return "2025-08-01"


def _slug(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())


def _result(status: str, competition: str, season: str, home: str, away: str, match_date: str, candidates: object, reason: str) -> dict[str, object]:
    return {
        "resolver_status": status,
        "match_date": match_date,
        "canonical_home_team": home,
        "canonical_away_team": away,
        "input_home_team": home,
        "input_away_team": away,
        "competition": competition,
        "season": season,
        "source_used": "v22_corpus",
        "candidates_count": len(candidates) if hasattr(candidates, "__len__") else 0,
        "candidates": _candidates(candidates),
        "confidence": 0.0 if status != "RESOLVED" else 1.0,
        "reason": reason,
        "reversed_fixture_found": False,
        "alias_matched": False,
    }


def _candidates(candidates: object) -> list[dict[str, object]]:
    if isinstance(candidates, pd.DataFrame):
        return candidates[["match_date", "home_team", "away_team"]].to_dict(orient="records") if not candidates.empty else []
    return []
