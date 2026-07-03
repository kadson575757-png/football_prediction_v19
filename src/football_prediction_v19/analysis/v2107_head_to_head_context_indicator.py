# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows


def build_head_to_head_context_indicator(
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
    h2h = _h2h_rows(matches, home_team, away_team).sort_values("match_date").tail(10)
    count = len(h2h)
    home_wins = away_wins = draws = 0
    goal_diffs: list[float] = []
    home_norm = normalize_team_or_league(home_team)
    for _, row in h2h.iterrows():
        is_home_side = normalize_team_or_league(row.get("home_team", "")) == home_norm
        gf = float(row.get("home_goals" if is_home_side else "away_goals", 0))
        ga = float(row.get("away_goals" if is_home_side else "home_goals", 0))
        goal_diffs.append(gf - ga)
        if gf > ga:
            home_wins += 1
        elif ga > gf:
            away_wins += 1
        else:
            draws += 1
    quality = "LOW" if count < 3 else ("FULL" if count >= 8 else "PARTIAL")
    home_rate = round(home_wins / count, 4) if count else 0.0
    away_rate = round(away_wins / count, 4) if count else 0.0
    draw_rate = round(draws / count, 4) if count else 0.0
    gd_avg = round(sum(goal_diffs) / count, 4) if count else 0.0
    signal = round((home_rate - away_rate) + gd_avg * 0.15, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and draw_rate >= 0.45:
        strength = min(0.02, draw_rate * 0.025)
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.25:
        strength = min(0.025, abs(signal) * 0.02)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality H2H context; no adjustment" if quality == "LOW" else ("H2H context near neutral; no adjustment" if not adjusted else "H2H context shifted diagnostic probability")
    result = build_shadow_result_dict("h2hc", "HEAD_TO_HEAD_CONTEXT_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"h2hc_matches_count": count, "h2hc_home_team_wins_count": home_wins, "h2hc_away_team_wins_count": away_wins, "h2hc_draws_count": draws, "h2hc_home_team_win_rate": home_rate, "h2hc_away_team_win_rate": away_rate, "h2hc_draw_rate": draw_rate, "h2hc_recent_h2h_goal_diff_average": gd_avg, "h2hc_context_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2107_head_to_head_context", cache_only=cache_only, enable_network=enable_network)


def _h2h_rows(frame: pd.DataFrame, home_team: str, away_team: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    home = normalize_team_or_league(home_team)
    away = normalize_team_or_league(away_team)
    norm_home = frame["home_team"].map(normalize_team_or_league)
    norm_away = frame["away_team"].map(normalize_team_or_league)
    return frame[((norm_home == home) & (norm_away == away)) | ((norm_home == away) & (norm_away == home))].copy()


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("h2hc", "HEAD_TO_HEAD_CONTEXT_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"h2hc_matches_count": 0, "h2hc_home_team_wins_count": 0, "h2hc_away_team_wins_count": 0, "h2hc_draws_count": 0, "h2hc_home_team_win_rate": 0.0, "h2hc_away_team_win_rate": 0.0, "h2hc_draw_rate": 0.0, "h2hc_recent_h2h_goal_diff_average": 0.0, "h2hc_context_signal": 0.0})
    return result
