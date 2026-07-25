# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, prior_rows, quality_from_match_counts, team_matches


def build_opponent_adjusted_recent_form_indicator(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    match_date: str,
    base_home_probability: float = 0.34,
    base_draw_probability: float = 0.32,
    base_away_probability: float = 0.34,
    source_profile: str | None = None,
    cache_only: bool = True,
    enable_network: bool = False,
) -> dict[str, object]:
    del source_profile
    if not competition or not season or not home_team or not away_team or not match_date:
        return _empty(base_home_probability, base_draw_probability, base_away_probability, "competition, season, teams and match_date are required")
    matches = prior_rows(_load_match_rows(competition, season, home_team, away_team, match_date, cache_only=cache_only, enable_network=enable_network), match_date)
    table_ppg = _season_ppg(matches)
    home_recent = team_matches(matches, home_team).sort_values("match_date").tail(5)
    away_recent = team_matches(matches, away_team).sort_values("match_date").tail(5)
    quality = quality_from_match_counts(len(home_recent), len(away_recent))
    home_points = _points(home_recent, home_team)
    away_points = _points(away_recent, away_team)
    home_ppm = round(home_points / len(home_recent), 4) if len(home_recent) else 0.0
    away_ppm = round(away_points / len(away_recent), 4) if len(away_recent) else 0.0
    home_opp = _recent_opponent_avg_ppg(home_recent, home_team, table_ppg)
    away_opp = _recent_opponent_avg_ppg(away_recent, away_team, table_ppg)
    home_adj = round(home_ppm * (1.0 + home_opp / 3.0), 4)
    away_adj = round(away_ppm * (1.0 + away_opp / 3.0), 4)
    diff = round(home_adj - away_adj, 4)
    strength = min(0.04, abs(diff) * 0.015) if quality != "LOW" and abs(diff) >= 0.35 else 0.0
    adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if diff > 0 else -strength) if strength else None
    reason = "LOW quality opponent-adjusted recent form; no adjustment" if quality == "LOW" else ("Opponent-adjusted recent form near neutral; no adjustment" if not strength else "Opponent-adjusted recent form shifted diagnostic probability")
    result = build_shadow_result_dict("oarf", "OPPONENT_ADJUSTED_RECENT_FORM", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result["shadow_explanation"] = str(result["oarf_shadow_explanation"])
    result.update({"oarf_home_recent_points": home_points, "oarf_away_recent_points": away_points, "oarf_home_recent_points_per_match": home_ppm, "oarf_away_recent_points_per_match": away_ppm, "oarf_home_recent_opponent_avg_ppg": home_opp, "oarf_away_recent_opponent_avg_ppg": away_opp, "oarf_home_quality_adjusted_form": home_adj, "oarf_away_quality_adjusted_form": away_adj, "oarf_quality_adjusted_form_diff": diff})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2106_opponent_adjusted_recent_form", cache_only=cache_only, enable_network=enable_network)


def _points(frame: pd.DataFrame, team: str) -> int:
    team_norm = normalize_team_or_league(team)
    points = 0
    for _, row in frame.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        hg = float(row.get("home_goals", 0))
        ag = float(row.get("away_goals", 0))
        is_home = home == team_norm
        gf, ga = (hg, ag) if is_home else (ag, hg)
        points += 3 if gf > ga else (1 if gf == ga else 0)
    return points


def _season_ppg(frame: pd.DataFrame) -> dict[str, float]:
    teams: dict[str, dict[str, int]] = {}
    for _, row in frame.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        away = normalize_team_or_league(row.get("away_team", ""))
        teams.setdefault(home, {"points": 0, "matches": 0})
        teams.setdefault(away, {"points": 0, "matches": 0})
        hg = float(row.get("home_goals", 0))
        ag = float(row.get("away_goals", 0))
        teams[home]["matches"] += 1
        teams[away]["matches"] += 1
        if hg > ag:
            teams[home]["points"] += 3
        elif ag > hg:
            teams[away]["points"] += 3
        else:
            teams[home]["points"] += 1
            teams[away]["points"] += 1
    return {team: round(v["points"] / v["matches"], 4) if v["matches"] else 0.0 for team, v in teams.items()}


def _recent_opponent_avg_ppg(frame: pd.DataFrame, team: str, ppg: dict[str, float]) -> float:
    team_norm = normalize_team_or_league(team)
    opponents = []
    for _, row in frame.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        away = normalize_team_or_league(row.get("away_team", ""))
        opponents.append(away if home == team_norm else home)
    return round(sum(ppg.get(opp, 0.0) for opp in opponents) / len(opponents), 4) if opponents else 0.0


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("oarf", "OPPONENT_ADJUSTED_RECENT_FORM", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result["shadow_explanation"] = str(result["oarf_shadow_explanation"])
    result.update({"oarf_home_recent_points": 0, "oarf_away_recent_points": 0, "oarf_home_recent_points_per_match": 0.0, "oarf_away_recent_points_per_match": 0.0, "oarf_home_recent_opponent_avg_ppg": 0.0, "oarf_away_recent_opponent_avg_ppg": 0.0, "oarf_home_quality_adjusted_form": 0.0, "oarf_away_quality_adjusted_form": 0.0, "oarf_quality_adjusted_form_diff": 0.0})
    return result
