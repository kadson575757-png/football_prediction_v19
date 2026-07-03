# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_recent_goal_trend_indicator(
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
    home_all = team_matches(matches, home_team).sort_values("match_date")
    away_all = team_matches(matches, away_team).sort_values("match_date")
    home_recent = home_all.tail(5)
    away_recent = away_all.tail(5)
    quality = quality_from_match_counts(len(home_recent), len(away_recent))
    hm = _rates(home_all, home_team, home_recent)
    aw = _rates(away_all, away_team, away_recent)
    net = round((hm["attacking_trend"] - hm["defensive_trend"]) - (aw["attacking_trend"] - aw["defensive_trend"]), 4)
    both_volatile = hm["attacking_trend"] > 0 and hm["defensive_trend"] > 0 and aw["attacking_trend"] > 0 and aw["defensive_trend"] > 0
    strength = min(0.035, abs(net) * 0.04) if quality != "LOW" and abs(net) >= 0.20 else (0.012 if quality != "LOW" and both_volatile else 0.0)
    adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength) if both_volatile and strength else (apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if net > 0 else -strength) if strength else None)
    reason = "LOW quality recent goal trend; no adjustment" if quality == "LOW" else ("Recent goal trend near neutral; no adjustment" if not strength else "Recent goal trend shifted diagnostic probabilities")
    result = build_shadow_result_dict("rgt", "RECENT_GOAL_TREND_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"rgt_home_recent_goals_for_per_match": hm["recent_gf"], "rgt_home_season_goals_for_per_match": hm["season_gf"], "rgt_home_attacking_trend": hm["attacking_trend"], "rgt_home_recent_goals_against_per_match": hm["recent_ga"], "rgt_home_season_goals_against_per_match": hm["season_ga"], "rgt_home_defensive_trend": hm["defensive_trend"], "rgt_away_recent_goals_for_per_match": aw["recent_gf"], "rgt_away_season_goals_for_per_match": aw["season_gf"], "rgt_away_attacking_trend": aw["attacking_trend"], "rgt_away_recent_goals_against_per_match": aw["recent_ga"], "rgt_away_season_goals_against_per_match": aw["season_ga"], "rgt_away_defensive_trend": aw["defensive_trend"], "rgt_net_trend_signal": net})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2106_recent_goal_trend", cache_only=cache_only, enable_network=enable_network)


def _rates(all_rows: pd.DataFrame, team: str, recent: pd.DataFrame) -> dict[str, float]:
    season_gf, season_ga = _gf_ga(all_rows, team)
    recent_gf, recent_ga = _gf_ga(recent, team)
    season_n = len(all_rows)
    recent_n = len(recent)
    season_gfpm = round(season_gf / season_n, 4) if season_n else 0.0
    season_gapm = round(season_ga / season_n, 4) if season_n else 0.0
    recent_gfpm = round(recent_gf / recent_n, 4) if recent_n else 0.0
    recent_gapm = round(recent_ga / recent_n, 4) if recent_n else 0.0
    return {"season_gf": season_gfpm, "season_ga": season_gapm, "recent_gf": recent_gfpm, "recent_ga": recent_gapm, "attacking_trend": round(recent_gfpm - season_gfpm, 4), "defensive_trend": round(recent_gapm - season_gapm, 4)}


def _gf_ga(frame: pd.DataFrame, team: str) -> tuple[float, float]:
    team_norm = normalize_team_or_league(team)
    gf = ga = 0.0
    for _, row in frame.iterrows():
        is_home = normalize_team_or_league(row.get("home_team", "")) == team_norm
        gf += float(row.get("home_goals" if is_home else "away_goals", 0))
        ga += float(row.get("away_goals" if is_home else "home_goals", 0))
    return gf, ga


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("rgt", "RECENT_GOAL_TREND_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({key: 0.0 for key in ["rgt_home_recent_goals_for_per_match", "rgt_home_season_goals_for_per_match", "rgt_home_attacking_trend", "rgt_home_recent_goals_against_per_match", "rgt_home_season_goals_against_per_match", "rgt_home_defensive_trend", "rgt_away_recent_goals_for_per_match", "rgt_away_season_goals_for_per_match", "rgt_away_attacking_trend", "rgt_away_recent_goals_against_per_match", "rgt_away_season_goals_against_per_match", "rgt_away_defensive_trend", "rgt_net_trend_signal"]})
    return result
