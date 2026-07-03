# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_heavy_result_exposure_indicator(
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
    home = _rates(home_rows, home_team)
    away = _rates(away_rows, away_team)
    home_fragility = round(home["big_loss"] + home["multi_loss"], 4)
    away_fragility = round(away["big_loss"] + away["multi_loss"], 4)
    signal = round((home["big_win"] + home["multi_win"] + away_fragility) - (away["big_win"] + away["multi_win"] + home_fragility), 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and max(abs(signal), home_fragility, away_fragility) < 0.18:
        strength = 0.008
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.18:
        strength = min(0.04, abs(signal) * 0.03)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality heavy result exposure profile; no adjustment" if quality == "LOW" else ("Heavy result exposure profile shifted diagnostic probability" if adjusted else "Heavy result exposure profile near neutral; no adjustment")
    result = build_shadow_result_dict("hre", "HEAVY_RESULT_EXPOSURE_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"hre_home_big_win_rate": home["big_win"], "hre_home_big_loss_rate": home["big_loss"], "hre_away_big_win_rate": away["big_win"], "hre_away_big_loss_rate": away["big_loss"], "hre_home_multi_goal_win_rate": home["multi_win"], "hre_home_multi_goal_loss_rate": home["multi_loss"], "hre_away_multi_goal_win_rate": away["multi_win"], "hre_away_multi_goal_loss_rate": away["multi_loss"], "hre_home_fragility_signal": home_fragility, "hre_away_fragility_signal": away_fragility, "hre_heavy_result_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2108_heavy_result_exposure", cache_only=cache_only, enable_network=enable_network)


def _rates(frame: pd.DataFrame, team: str) -> dict[str, float]:
    team_norm = normalize_team_or_league(team)
    margins = []
    for _, row in frame.iterrows():
        is_home = normalize_team_or_league(row.get("home_team", "")) == team_norm
        gf = float(row.get("home_goals" if is_home else "away_goals", 0))
        ga = float(row.get("away_goals" if is_home else "home_goals", 0))
        margins.append(gf - ga)
    n = len(margins)
    if not n:
        return {"big_win": 0.0, "big_loss": 0.0, "multi_win": 0.0, "multi_loss": 0.0}
    return {
        "big_win": round(sum(1 for margin in margins if margin >= 3) / n, 4),
        "big_loss": round(sum(1 for margin in margins if margin <= -3) / n, 4),
        "multi_win": round(sum(1 for margin in margins if margin >= 2) / n, 4),
        "multi_loss": round(sum(1 for margin in margins if margin <= -2) / n, 4),
    }


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("hre", "HEAVY_RESULT_EXPOSURE_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"hre_home_big_win_rate": 0.0, "hre_home_big_loss_rate": 0.0, "hre_away_big_win_rate": 0.0, "hre_away_big_loss_rate": 0.0, "hre_home_multi_goal_win_rate": 0.0, "hre_home_multi_goal_loss_rate": 0.0, "hre_away_multi_goal_win_rate": 0.0, "hre_away_multi_goal_loss_rate": 0.0, "hre_home_fragility_signal": 0.0, "hre_away_fragility_signal": 0.0, "hre_heavy_result_signal": 0.0})
    return result
