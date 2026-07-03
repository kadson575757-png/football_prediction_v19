# -*- coding: utf-8 -*-
from __future__ import annotations

import statistics

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_result_volatility_consistency_indicator(
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
    quality = quality_from_match_counts(len(home_rows), len(away_rows))
    home_margins = _margins(home_rows, home_team)
    away_margins = _margins(away_rows, away_team)
    home_std = round(statistics.pstdev(home_margins), 4) if len(home_margins) > 1 else 0.0
    away_std = round(statistics.pstdev(away_margins), 4) if len(away_margins) > 1 else 0.0
    home_consistency = _consistency_rate(home_margins)
    away_consistency = _consistency_rate(away_margins)
    volatility = round((home_std + away_std) / 2, 4)
    consistency = round((home_consistency + away_consistency) / 2, 4)
    signal = round(volatility - consistency, 4)
    home_avg = sum(home_margins) / len(home_margins) if home_margins else 0.0
    away_avg = sum(away_margins) / len(away_margins) if away_margins else 0.0
    strength = 0.0
    adjusted = None
    if quality != "LOW" and volatility >= 1.8:
        strength = min(0.025, (volatility - 1.5) * 0.01)
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and max(home_consistency, away_consistency) >= 0.65 and abs(home_avg - away_avg) >= 0.4:
        strength = 0.018
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if home_avg > away_avg else -strength)
    reason = "LOW quality result volatility/consistency profile; no adjustment" if quality == "LOW" else ("Result volatility/consistency profile near neutral; no adjustment" if not strength else "Result volatility/consistency profile shifted diagnostic probability")
    result = build_shadow_result_dict("rvc", "RESULT_VOLATILITY_CONSISTENCY_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"rvc_home_goal_diff_std": home_std, "rvc_away_goal_diff_std": away_std, "rvc_home_result_consistency_rate": home_consistency, "rvc_away_result_consistency_rate": away_consistency, "rvc_combined_volatility_score": volatility, "rvc_combined_consistency_score": consistency, "rvc_volatility_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2106_result_volatility_consistency", cache_only=cache_only, enable_network=enable_network)


def _margins(frame: pd.DataFrame, team: str) -> list[float]:
    team_norm = normalize_team_or_league(team)
    margins = []
    for _, row in frame.iterrows():
        is_home = normalize_team_or_league(row.get("home_team", "")) == team_norm
        gf = float(row.get("home_goals" if is_home else "away_goals", 0))
        ga = float(row.get("away_goals" if is_home else "home_goals", 0))
        margins.append(gf - ga)
    return margins


def _consistency_rate(margins: list[float]) -> float:
    if not margins:
        return 0.0
    return round(sum(1 for margin in margins if abs(margin) <= 1) / len(margins), 4)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("rvc", "RESULT_VOLATILITY_CONSISTENCY_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"rvc_home_goal_diff_std": 0.0, "rvc_away_goal_diff_std": 0.0, "rvc_home_result_consistency_rate": 0.0, "rvc_away_result_consistency_rate": 0.0, "rvc_combined_volatility_score": 0.0, "rvc_combined_consistency_score": 0.0, "rvc_volatility_signal": 0.0})
    return result
