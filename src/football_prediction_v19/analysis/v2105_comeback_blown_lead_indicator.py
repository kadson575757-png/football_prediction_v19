# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, prior_rows, quality_from_match_counts, team_matches


def build_comeback_blown_lead_indicator(
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
    if not {"half_home_goals", "half_away_goals"}.issubset(matches.columns):
        return _empty(base_home_probability, base_draw_probability, base_away_probability, "Halftime/result-path data unavailable; no adjustment.")
    home_rows = team_matches(matches, home_team)
    away_rows = team_matches(matches, away_team)
    quality = quality_from_match_counts(len(home_rows), len(away_rows))
    home_stats = _path_stats(home_rows, home_team)
    away_stats = _path_stats(away_rows, away_team)
    stability_signal = round(home_stats["lead_to_win_rate"] - away_stats["lead_to_win_rate"], 4)
    comeback_signal = round(home_stats["trail_to_result_rate"] - away_stats["trail_to_result_rate"], 4)
    signal = round(stability_signal + comeback_signal * 0.5, 4)
    strength = min(0.035, abs(signal) * 0.035) if quality != "LOW" and abs(signal) >= 0.20 else 0.0
    adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength) if strength else None
    reason = "LOW quality comeback/blown-lead profile; no adjustment" if quality == "LOW" else ("Comeback/blown-lead profile near neutral; no adjustment" if not strength else "Comeback/blown-lead profile shifted diagnostic probability")
    result = build_shadow_result_dict("cbl", "COMEBACK_BLOWN_LEAD_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update(
        {
            "cbl_home_lead_to_win_rate": home_stats["lead_to_win_rate"],
            "cbl_home_lead_to_nonwin_rate": home_stats["lead_to_nonwin_rate"],
            "cbl_home_trail_to_result_rate": home_stats["trail_to_result_rate"],
            "cbl_away_lead_to_win_rate": away_stats["lead_to_win_rate"],
            "cbl_away_lead_to_nonwin_rate": away_stats["lead_to_nonwin_rate"],
            "cbl_away_trail_to_result_rate": away_stats["trail_to_result_rate"],
            "cbl_stability_signal": stability_signal,
            "cbl_comeback_signal": comeback_signal,
        }
    )
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2105_comeback_blown_lead", cache_only=cache_only, enable_network=enable_network)


def _path_stats(frame: pd.DataFrame, team: str) -> dict[str, float]:
    team_norm = normalize_team_or_league(team)
    leads = lead_wins = trails = trail_results = 0
    for _, row in frame.iterrows():
        is_home = normalize_team_or_league(row.get("home_team", "")) == team_norm
        ht_for = float(row.get("half_home_goals" if is_home else "half_away_goals", 0))
        ht_against = float(row.get("half_away_goals" if is_home else "half_home_goals", 0))
        ft_for = float(row.get("home_goals" if is_home else "away_goals", 0))
        ft_against = float(row.get("away_goals" if is_home else "home_goals", 0))
        if ht_for > ht_against:
            leads += 1
            if ft_for > ft_against:
                lead_wins += 1
        elif ht_for < ht_against:
            trails += 1
            if ft_for >= ft_against:
                trail_results += 1
    lead_rate = round(lead_wins / leads, 4) if leads else 0.0
    trail_rate = round(trail_results / trails, 4) if trails else 0.0
    return {"lead_to_win_rate": lead_rate, "lead_to_nonwin_rate": round(1.0 - lead_rate, 4) if leads else 0.0, "trail_to_result_rate": trail_rate}


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("cbl", "COMEBACK_BLOWN_LEAD_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"cbl_home_lead_to_win_rate": 0.0, "cbl_home_lead_to_nonwin_rate": 0.0, "cbl_home_trail_to_result_rate": 0.0, "cbl_away_lead_to_win_rate": 0.0, "cbl_away_lead_to_nonwin_rate": 0.0, "cbl_away_trail_to_result_rate": 0.0, "cbl_stability_signal": 0.0, "cbl_comeback_signal": 0.0})
    return result
