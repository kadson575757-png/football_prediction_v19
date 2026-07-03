# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches, venue_matches


def build_venue_split_delta_indicator(
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
    home_all = team_matches(matches, home_team)
    away_all = team_matches(matches, away_team)
    home_home = venue_matches(matches, home_team, "home")
    away_away = venue_matches(matches, away_team, "away")
    quality = quality_from_match_counts(len(home_home), len(away_away))
    ho_ppg, ho_gd = _rates(home_all, home_team)
    hh_ppg, hh_gd = _rates(home_home, home_team)
    ao_ppg, ao_gd = _rates(away_all, away_team)
    aa_ppg, aa_gd = _rates(away_away, away_team)
    home_ppg_delta = round(hh_ppg - ho_ppg, 4)
    away_ppg_delta = round(aa_ppg - ao_ppg, 4)
    home_gd_delta = round(hh_gd - ho_gd, 4)
    away_gd_delta = round(aa_gd - ao_gd, 4)
    signal = round((home_ppg_delta - away_ppg_delta) + (home_gd_delta - away_gd_delta) * 0.25, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and abs(signal) < 0.12:
        strength = 0.008
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.12:
        strength = min(0.04, abs(signal) * 0.025)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality venue split delta; no adjustment" if quality == "LOW" else ("Venue split delta shifted diagnostic probability" if adjusted else "Venue split delta near neutral; no adjustment")
    result = build_shadow_result_dict("vsd", "VENUE_SPLIT_DELTA_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"vsd_home_overall_ppg": ho_ppg, "vsd_home_home_ppg": hh_ppg, "vsd_home_venue_ppg_delta": home_ppg_delta, "vsd_away_overall_ppg": ao_ppg, "vsd_away_away_ppg": aa_ppg, "vsd_away_venue_ppg_delta": away_ppg_delta, "vsd_home_overall_goal_diff_per_match": ho_gd, "vsd_home_home_goal_diff_per_match": hh_gd, "vsd_home_venue_goal_diff_delta": home_gd_delta, "vsd_away_overall_goal_diff_per_match": ao_gd, "vsd_away_away_goal_diff_per_match": aa_gd, "vsd_away_venue_goal_diff_delta": away_gd_delta, "vsd_venue_split_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2109_venue_split_delta", cache_only=cache_only, enable_network=enable_network)


def _rates(frame: pd.DataFrame, team: str) -> tuple[float, float]:
    if frame.empty:
        return 0.0, 0.0
    points = 0
    gd = 0.0
    for _, row in frame.iterrows():
        is_home = str(row.get("home_team", "")).casefold() == str(team).casefold()
        gf = float(row.get("home_goals" if is_home else "away_goals", 0))
        ga = float(row.get("away_goals" if is_home else "home_goals", 0))
        gd += gf - ga
        points += 3 if gf > ga else (1 if gf == ga else 0)
    return round(points / len(frame), 4), round(gd / len(frame), 4)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("vsd", "VENUE_SPLIT_DELTA_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"vsd_home_overall_ppg": 0.0, "vsd_home_home_ppg": 0.0, "vsd_home_venue_ppg_delta": 0.0, "vsd_away_overall_ppg": 0.0, "vsd_away_away_ppg": 0.0, "vsd_away_venue_ppg_delta": 0.0, "vsd_home_overall_goal_diff_per_match": 0.0, "vsd_home_home_goal_diff_per_match": 0.0, "vsd_home_venue_goal_diff_delta": 0.0, "vsd_away_overall_goal_diff_per_match": 0.0, "vsd_away_away_goal_diff_per_match": 0.0, "vsd_away_venue_goal_diff_delta": 0.0, "vsd_venue_split_signal": 0.0})
    return result
