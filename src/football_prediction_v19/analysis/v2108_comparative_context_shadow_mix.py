# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from football_prediction_v19.analysis.v2105_further_indicator_shadow_mix import _build_mix


PREFIX_BY_NAME = {
    "COMMON_OPPONENT_PERFORMANCE_PROFILE": "cop",
    "STRENGTH_BAND_PERFORMANCE_PROFILE": "sbp",
    "RESPONSE_AFTER_RESULT_PROFILE": "rar",
    "HEAVY_RESULT_EXPOSURE_PROFILE": "hre",
}


def build_v2108_comparative_context_shadow_mix(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    indicator_results: list[dict[str, Any]] | dict[str, dict[str, Any]],
    weights: dict[str, float] | None = None,
    max_total_shift: float = 0.06,
) -> dict[str, object]:
    return _build_mix("v2108_mix", base_home_probability, base_draw_probability, base_away_probability, indicator_results, weights, max_total_shift, PREFIX_BY_NAME)
