# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, venue_matches


def build_venue_recent_momentum_indicator(
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
    home_recent = venue_matches(matches, home_team, "home").sort_values("match_date").tail(5)
    away_recent = venue_matches(matches, away_team, "away").sort_values("match_date").tail(5)
    quality = quality_from_match_counts(len(home_recent), len(away_recent))
    home_points, home_gd = _venue_points_gd(home_recent, "home")
    away_points, away_gd = _venue_points_gd(away_recent, "away")
    home_ppg = round(home_points / len(home_recent), 4) if len(home_recent) else 0.0
    away_ppg = round(away_points / len(away_recent), 4) if len(away_recent) else 0.0
    home_gdpm = round(home_gd / len(home_recent), 4) if len(home_recent) else 0.0
    away_gdpm = round(away_gd / len(away_recent), 4) if len(away_recent) else 0.0
    signal = round((home_ppg - away_ppg) + (home_gdpm - away_gdpm) * 0.35, 4)
    strength = 0.012 if quality != "LOW" and abs(signal) < 0.15 else (min(0.04, abs(signal) * 0.02) if quality != "LOW" and abs(signal) >= 0.25 else 0.0)
    adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength) if strength and abs(signal) < 0.15 else (apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength) if strength else None)
    reason = "LOW quality venue recent momentum; no adjustment" if quality == "LOW" else ("Venue recent momentum near neutral; draw shadow increased slightly" if adjusted and abs(signal) < 0.15 else ("Venue recent momentum near neutral; no adjustment" if not adjusted else "Venue recent momentum shifted diagnostic probability"))
    result = build_shadow_result_dict("vrm", "VENUE_RECENT_MOMENTUM_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"vrm_home_recent_home_matches_count": len(home_recent), "vrm_away_recent_away_matches_count": len(away_recent), "vrm_home_recent_home_points": home_points, "vrm_away_recent_away_points": away_points, "vrm_home_recent_home_ppg": home_ppg, "vrm_away_recent_away_ppg": away_ppg, "vrm_home_recent_home_goal_diff_per_match": home_gdpm, "vrm_away_recent_away_goal_diff_per_match": away_gdpm, "vrm_venue_momentum_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2106_venue_recent_momentum", cache_only=cache_only, enable_network=enable_network)


def _venue_points_gd(frame: pd.DataFrame, venue: str) -> tuple[int, float]:
    points = 0
    gd = 0.0
    for _, row in frame.iterrows():
        gf = float(row.get("home_goals" if venue == "home" else "away_goals", 0))
        ga = float(row.get("away_goals" if venue == "home" else "home_goals", 0))
        gd += gf - ga
        points += 3 if gf > ga else (1 if gf == ga else 0)
    return points, gd


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("vrm", "VENUE_RECENT_MOMENTUM_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"vrm_home_recent_home_matches_count": 0, "vrm_away_recent_away_matches_count": 0, "vrm_home_recent_home_points": 0, "vrm_away_recent_away_points": 0, "vrm_home_recent_home_ppg": 0.0, "vrm_away_recent_away_ppg": 0.0, "vrm_home_recent_home_goal_diff_per_match": 0.0, "vrm_away_recent_away_goal_diff_per_match": 0.0, "vrm_venue_momentum_signal": 0.0})
    return result
