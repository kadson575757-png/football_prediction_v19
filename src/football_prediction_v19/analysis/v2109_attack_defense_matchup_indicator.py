# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches, venue_matches


def build_attack_defense_matchup_indicator(
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
    home_home = venue_matches(matches, home_team, "home")
    away_away = venue_matches(matches, away_team, "away")
    quality = quality_from_match_counts(len(home_home), len(away_away))
    hgf, hga = _gf_ga_rates(home_home, "home")
    agf, aga = _gf_ga_rates(away_away, "away")
    home_signal = round(hgf + aga, 4)
    away_signal = round(agf + hga, 4)
    matchup_signal = round(home_signal - away_signal, 4)
    edge = round(abs(matchup_signal), 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and edge < 0.18:
        strength = 0.01
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and edge >= 0.18:
        strength = min(0.04, edge * 0.025)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if matchup_signal > 0 else -strength)
    reason = "LOW quality attack/defense matchup; no adjustment" if quality == "LOW" else ("Attack/defense matchup shifted diagnostic probability" if adjusted else "Attack/defense matchup near neutral; no adjustment")
    result = build_shadow_result_dict("adm", "ATTACK_DEFENSE_MATCHUP_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"adm_home_home_goals_for_per_match": hgf, "adm_home_home_goals_against_per_match": hga, "adm_away_away_goals_for_per_match": agf, "adm_away_away_goals_against_per_match": aga, "adm_home_attack_vs_away_defense_signal": home_signal, "adm_away_attack_vs_home_defense_signal": away_signal, "adm_matchup_signal": matchup_signal, "adm_attack_defense_edge": edge})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2109_attack_defense_matchup", cache_only=cache_only, enable_network=enable_network)


def _gf_ga_rates(frame: pd.DataFrame, venue: str) -> tuple[float, float]:
    if frame.empty:
        return 0.0, 0.0
    gf_col = "home_goals" if venue == "home" else "away_goals"
    ga_col = "away_goals" if venue == "home" else "home_goals"
    return round(float(frame[gf_col].astype(float).sum()) / len(frame), 4), round(float(frame[ga_col].astype(float).sum()) / len(frame), 4)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("adm", "ATTACK_DEFENSE_MATCHUP_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"adm_home_home_goals_for_per_match": 0.0, "adm_home_home_goals_against_per_match": 0.0, "adm_away_away_goals_for_per_match": 0.0, "adm_away_away_goals_against_per_match": 0.0, "adm_home_attack_vs_away_defense_signal": 0.0, "adm_away_attack_vs_home_defense_signal": 0.0, "adm_matchup_signal": 0.0, "adm_attack_defense_edge": 0.0})
    return result
