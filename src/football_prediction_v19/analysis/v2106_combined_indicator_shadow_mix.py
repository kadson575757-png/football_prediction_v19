# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from football_prediction_v19.analysis.v2105_further_indicator_shadow_mix import _build_mix


COMBINED_PREFIX_BY_NAME = {
    "DRAW_TENDENCY": "dt",
    "VENUE_RESULT_RATE": "vr",
    "GOAL_MARGIN_PROFILE": "gm",
    "VENUE_SCORING_BALANCE": "vsb",
    "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE": "csfts",
    "REST_DAYS_CONGESTION_PROFILE": "rdc",
    "TABLE_STRENGTH_GAP_PROFILE": "tsg",
    "COMEBACK_BLOWN_LEAD_PROFILE": "cbl",
    "OPPONENT_ADJUSTED_RECENT_FORM": "oarf",
    "RECENT_GOAL_TREND_PROFILE": "rgt",
    "VENUE_RECENT_MOMENTUM_PROFILE": "vrm",
    "RESULT_VOLATILITY_CONSISTENCY_PROFILE": "rvc",
}


def build_v2106_combined_indicator_shadow_mix(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    indicator_results: list[dict[str, Any]] | dict[str, dict[str, Any]],
    weights: dict[str, float] | None = None,
    max_total_shift: float = 0.10,
) -> dict[str, object]:
    return _build_mix("v2106_combined_mix", base_home_probability, base_draw_probability, base_away_probability, indicator_results, weights, max_total_shift, COMBINED_PREFIX_BY_NAME)
