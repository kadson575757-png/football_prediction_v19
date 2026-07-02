# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import (
    apply_home_away_shift,
    build_shadow_result_dict,
    load_match_rows,
    preserve_home_away_ratio_adjust_draw,
    prior_rows,
    quality_from_match_counts,
    venue_matches,
)


def build_clean_sheet_failed_to_score_indicator(
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
    home_cs = round(float(home_rows["away_goals"].astype(float).eq(0).sum() / home_n), 4) if home_n else 0.0
    home_fts = round(float(home_rows["home_goals"].astype(float).eq(0).sum() / home_n), 4) if home_n else 0.0
    away_cs = round(float(away_rows["home_goals"].astype(float).eq(0).sum() / away_n), 4) if away_n else 0.0
    away_fts = round(float(away_rows["away_goals"].astype(float).eq(0).sum() / away_n), 4) if away_n else 0.0
    home_signal = round(home_cs + away_fts, 4)
    away_signal = round(away_cs + home_fts, 4)
    draw_signal = round((home_fts + away_fts + home_cs + away_cs) / 2, 4)
    edge = round(max(home_signal, away_signal, draw_signal) - sorted([home_signal, away_signal, draw_signal], reverse=True)[1], 4)
    strength = min(0.04, edge * 0.08) if quality != "LOW" and edge >= 0.15 else 0.0
    adjusted = None
    if strength and home_signal >= away_signal and home_signal >= draw_signal:
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif strength and away_signal >= home_signal and away_signal >= draw_signal:
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, -strength)
    elif strength:
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    reason = "LOW quality clean-sheet/failed-to-score profile; no adjustment" if quality == "LOW" else ("Clean-sheet/failed-to-score signals too close; no adjustment" if not strength else "Clean-sheet/failed-to-score profile shifted diagnostic probabilities")
    result = build_shadow_result_dict("csfts", "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update(
        {
            "csfts_home_clean_sheet_rate": home_cs,
            "csfts_home_failed_to_score_rate": home_fts,
            "csfts_away_clean_sheet_rate": away_cs,
            "csfts_away_failed_to_score_rate": away_fts,
            "csfts_home_defensive_signal": home_signal,
            "csfts_home_attacking_risk": home_fts,
            "csfts_away_defensive_signal": away_signal,
            "csfts_away_attacking_risk": away_fts,
            "csfts_signal_edge": edge,
        }
    )
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2105_clean_sheet_failed_to_score", cache_only=cache_only, enable_network=enable_network)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("csfts", "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({key: 0.0 for key in ["csfts_home_clean_sheet_rate", "csfts_home_failed_to_score_rate", "csfts_away_clean_sheet_rate", "csfts_away_failed_to_score_rate", "csfts_home_defensive_signal", "csfts_home_attacking_risk", "csfts_away_defensive_signal", "csfts_away_attacking_risk", "csfts_signal_edge"]})
    return result
