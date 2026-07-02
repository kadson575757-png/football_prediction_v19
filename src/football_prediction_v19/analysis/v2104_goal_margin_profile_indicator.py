# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import (
    apply_home_away_shift,
    build_shadow_result_dict,
    load_match_rows,
    preserve_home_away_ratio_adjust_draw,
    prior_rows,
    quality_from_match_counts,
    team_matches,
)


def build_goal_margin_profile_indicator(
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
    home_rows = team_matches(matches, home_team)
    away_rows = team_matches(matches, away_team)
    home_n = len(home_rows)
    away_n = len(away_rows)
    quality = quality_from_match_counts(home_n, away_n)
    home_margin = _average_margin(home_rows, home_team)
    away_margin = _average_margin(away_rows, away_team)
    diff = round(home_margin - away_margin, 4)
    home_narrow = _narrow_rate(home_rows)
    away_narrow = _narrow_rate(away_rows)
    combined_narrow = round((home_narrow + away_narrow) / 2, 4) if home_n and away_n else 0.0
    strength = 0.0
    adjusted = None
    if quality != "LOW" and combined_narrow >= 0.55:
        strength = min(0.03, (combined_narrow - 0.50) * 0.08)
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(diff) >= 0.35:
        strength = min(0.035, abs(diff) * 0.025)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if diff > 0 else -strength)
    reason = "LOW quality goal margin profile; no adjustment" if quality == "LOW" else ("Goal margin profile near neutral; no adjustment" if not strength else "Goal margin profile shifted diagnostic probabilities")
    result = build_shadow_result_dict("gm", "GOAL_MARGIN_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update(
        {
            "gm_home_average_goal_margin": home_margin,
            "gm_away_average_goal_margin": away_margin,
            "gm_goal_margin_diff": diff,
            "gm_home_narrow_match_rate": home_narrow,
            "gm_away_narrow_match_rate": away_narrow,
            "gm_combined_narrow_match_rate": combined_narrow,
        }
    )
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2104_goal_margin_profile", cache_only=cache_only, enable_network=enable_network)


def _average_margin(frame: pd.DataFrame, team: str) -> float:
    team_norm = normalize_team_or_league(team)
    margins = []
    for _, row in frame.iterrows():
        home_goals = float(row.get("home_goals", 0))
        away_goals = float(row.get("away_goals", 0))
        if normalize_team_or_league(row.get("home_team", "")) == team_norm:
            margins.append(home_goals - away_goals)
        elif normalize_team_or_league(row.get("away_team", "")) == team_norm:
            margins.append(away_goals - home_goals)
    return round(sum(margins) / len(margins), 4) if margins else 0.0


def _narrow_rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return 0.0
    margins = (frame["home_goals"].astype(float) - frame["away_goals"].astype(float)).abs()
    return round(float(margins.le(1).sum() / len(frame)), 4)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("gm", "GOAL_MARGIN_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update(
        {
            "gm_home_average_goal_margin": 0.0,
            "gm_away_average_goal_margin": 0.0,
            "gm_goal_margin_diff": 0.0,
            "gm_home_narrow_match_rate": 0.0,
            "gm_away_narrow_match_rate": 0.0,
            "gm_combined_narrow_match_rate": 0.0,
        }
    )
    return result
