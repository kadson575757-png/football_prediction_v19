# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows
from football_prediction_v19.analysis.v2107_league_zone_pressure_indicator import _table, _zone


def build_strength_band_performance_indicator(
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
    table = _table(matches)
    teams_count = len(table)
    zones = {team: _zone(values["rank"], teams_count) for team, values in table.items()}
    home_zone = zones.get(normalize_team_or_league(home_team), "unknown")
    away_zone = zones.get(normalize_team_or_league(away_team), "unknown")
    home = _performance_vs_zone(matches, home_team, away_zone, zones)
    away = _performance_vs_zone(matches, away_team, home_zone, zones)
    quality = "FULL" if home["matches"] >= 8 and away["matches"] >= 8 else ("PARTIAL" if home["matches"] >= 3 and away["matches"] >= 3 else "LOW")
    home_ppg = round(home["points"] / home["matches"], 4) if home["matches"] else 0.0
    away_ppg = round(away["points"] / away["matches"], 4) if away["matches"] else 0.0
    signal = round((home_ppg - away_ppg) + (home["gd"] - away["gd"]) * 0.05, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and abs(signal) < 0.15:
        strength = 0.01
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.15:
        strength = min(0.04, abs(signal) * 0.025)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality strength band profile; no adjustment" if quality == "LOW" else ("Strength band profile shifted diagnostic probability" if adjusted else "Strength band profile near neutral; no adjustment")
    result = build_shadow_result_dict("sbp", "STRENGTH_BAND_PERFORMANCE_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"sbp_home_target_opponent_zone": away_zone, "sbp_away_target_opponent_zone": home_zone, "sbp_home_points_vs_away_zone": int(home["points"]), "sbp_away_points_vs_home_zone": int(away["points"]), "sbp_home_ppg_vs_away_zone": home_ppg, "sbp_away_ppg_vs_home_zone": away_ppg, "sbp_home_goal_diff_vs_away_zone": int(home["gd"]), "sbp_away_goal_diff_vs_home_zone": int(away["gd"]), "sbp_strength_band_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2108_strength_band_performance", cache_only=cache_only, enable_network=enable_network)


def _performance_vs_zone(frame: pd.DataFrame, team: str, target_zone: str, zones: dict[str, str]) -> dict[str, int]:
    team_norm = normalize_team_or_league(team)
    out = {"points": 0, "gd": 0, "matches": 0}
    for _, row in frame.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        away = normalize_team_or_league(row.get("away_team", ""))
        if team_norm not in {home, away}:
            continue
        opponent = away if home == team_norm else home
        if zones.get(opponent, "unknown") != target_zone:
            continue
        gf = int(float(row.get("home_goals" if home == team_norm else "away_goals", 0)))
        ga = int(float(row.get("away_goals" if home == team_norm else "home_goals", 0)))
        out["points"] += 3 if gf > ga else (1 if gf == ga else 0)
        out["gd"] += gf - ga
        out["matches"] += 1
    return out


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("sbp", "STRENGTH_BAND_PERFORMANCE_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"sbp_home_target_opponent_zone": "unknown", "sbp_away_target_opponent_zone": "unknown", "sbp_home_points_vs_away_zone": 0, "sbp_away_points_vs_home_zone": 0, "sbp_home_ppg_vs_away_zone": 0.0, "sbp_away_ppg_vs_home_zone": 0.0, "sbp_home_goal_diff_vs_away_zone": 0, "sbp_away_goal_diff_vs_home_zone": 0, "sbp_strength_band_signal": 0.0})
    return result
