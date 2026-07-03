# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows


def build_common_opponent_performance_indicator(
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
    home_perf = _opponent_performance(matches, home_team)
    away_perf = _opponent_performance(matches, away_team)
    common = sorted(set(home_perf) & set(away_perf))
    home_points = sum(home_perf[opp]["points"] for opp in common)
    away_points = sum(away_perf[opp]["points"] for opp in common)
    home_gd = sum(home_perf[opp]["gd"] for opp in common)
    away_gd = sum(away_perf[opp]["gd"] for opp in common)
    home_matches = sum(home_perf[opp]["matches"] for opp in common)
    away_matches = sum(away_perf[opp]["matches"] for opp in common)
    count = len(common)
    quality = "FULL" if count >= 8 else ("PARTIAL" if count >= 3 else "LOW")
    home_ppg = round(home_points / home_matches, 4) if home_matches else 0.0
    away_ppg = round(away_points / away_matches, 4) if away_matches else 0.0
    ppg_gap = round(home_ppg - away_ppg, 4)
    gd_gap = round(home_gd - away_gd, 4)
    signal = round(ppg_gap + gd_gap * 0.08, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and abs(signal) < 0.18:
        strength = 0.01
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.18:
        strength = min(0.04, abs(signal) * 0.025)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality common opponent profile; no adjustment" if quality == "LOW" else ("Common opponent profile shifted diagnostic probability" if adjusted else "Common opponent profile near neutral; no adjustment")
    result = build_shadow_result_dict("cop", "COMMON_OPPONENT_PERFORMANCE_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"cop_common_opponents_count": count, "cop_home_points_vs_common_opponents": int(home_points), "cop_away_points_vs_common_opponents": int(away_points), "cop_home_ppg_vs_common_opponents": home_ppg, "cop_away_ppg_vs_common_opponents": away_ppg, "cop_home_goal_diff_vs_common_opponents": int(home_gd), "cop_away_goal_diff_vs_common_opponents": int(away_gd), "cop_goal_diff_gap_vs_common_opponents": gd_gap, "cop_ppg_gap_vs_common_opponents": ppg_gap, "cop_common_opponent_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2108_common_opponent_performance", cache_only=cache_only, enable_network=enable_network)


def _opponent_performance(frame: pd.DataFrame, team: str) -> dict[str, dict[str, int]]:
    team_norm = normalize_team_or_league(team)
    out: dict[str, dict[str, int]] = {}
    for _, row in frame.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        away = normalize_team_or_league(row.get("away_team", ""))
        if team_norm not in {home, away}:
            continue
        opponent = away if home == team_norm else home
        gf = int(float(row.get("home_goals" if home == team_norm else "away_goals", 0)))
        ga = int(float(row.get("away_goals" if home == team_norm else "home_goals", 0)))
        out.setdefault(opponent, {"points": 0, "gd": 0, "matches": 0})
        out[opponent]["points"] += 3 if gf > ga else (1 if gf == ga else 0)
        out[opponent]["gd"] += gf - ga
        out[opponent]["matches"] += 1
    return out


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("cop", "COMMON_OPPONENT_PERFORMANCE_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"cop_common_opponents_count": 0, "cop_home_points_vs_common_opponents": 0, "cop_away_points_vs_common_opponents": 0, "cop_home_ppg_vs_common_opponents": 0.0, "cop_away_ppg_vs_common_opponents": 0.0, "cop_home_goal_diff_vs_common_opponents": 0, "cop_away_goal_diff_vs_common_opponents": 0, "cop_goal_diff_gap_vs_common_opponents": 0.0, "cop_ppg_gap_vs_common_opponents": 0.0, "cop_common_opponent_signal": 0.0})
    return result
