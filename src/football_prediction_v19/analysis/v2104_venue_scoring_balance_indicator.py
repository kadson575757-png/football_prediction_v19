# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import (
    apply_home_away_shift,
    build_shadow_result_dict,
    load_match_rows,
    prior_rows,
    quality_from_match_counts,
    venue_matches,
)


def build_venue_scoring_balance_indicator(
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
    home_rows = venue_matches(matches, home_team, "home")
    away_rows = venue_matches(matches, away_team, "away")
    home_n = len(home_rows)
    away_n = len(away_rows)
    quality = quality_from_match_counts(home_n, away_n)
    home_gf = round(float(home_rows["home_goals"].astype(float).sum() / home_n), 4) if home_n else 0.0
    home_ga = round(float(home_rows["away_goals"].astype(float).sum() / home_n), 4) if home_n else 0.0
    away_gf = round(float(away_rows["away_goals"].astype(float).sum() / away_n), 4) if away_n else 0.0
    away_ga = round(float(away_rows["home_goals"].astype(float).sum() / away_n), 4) if away_n else 0.0
    home_pressure = round(home_gf + away_ga, 4)
    away_pressure = round(away_gf + home_ga, 4)
    diff = round(home_pressure - away_pressure, 4)
    strength = min(0.04, abs(diff) * 0.025) if quality != "LOW" and abs(diff) >= 0.25 else 0.0
    adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if diff > 0 else -strength) if strength else None
    reason = "LOW quality venue scoring balance; no adjustment" if quality == "LOW" else ("Venue scoring pressure near neutral; no adjustment" if not strength else "Venue scoring pressure shifted diagnostic home/away probability")
    result = build_shadow_result_dict("vsb", "VENUE_SCORING_BALANCE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update(
        {
            "vsb_home_home_goals_for_per_match": home_gf,
            "vsb_home_home_goals_against_per_match": home_ga,
            "vsb_away_away_goals_for_per_match": away_gf,
            "vsb_away_away_goals_against_per_match": away_ga,
            "vsb_home_goal_pressure": home_pressure,
            "vsb_away_goal_pressure": away_pressure,
            "vsb_goal_pressure_diff": diff,
        }
    )
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2104_venue_scoring_balance", cache_only=cache_only, enable_network=enable_network)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("vsb", "VENUE_SCORING_BALANCE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update(
        {
            "vsb_home_home_goals_for_per_match": 0.0,
            "vsb_home_home_goals_against_per_match": 0.0,
            "vsb_away_away_goals_for_per_match": 0.0,
            "vsb_away_away_goals_against_per_match": 0.0,
            "vsb_home_goal_pressure": 0.0,
            "vsb_away_goal_pressure": 0.0,
            "vsb_goal_pressure_diff": 0.0,
        }
    )
    return result
