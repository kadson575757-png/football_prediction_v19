# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from football_prediction_v19.analysis.v2105_further_indicator_shadow_mix import _build_mix


PREFIX_BY_NAME = {
    "RESULT_STREAK_PROFILE": "rsp",
    "SCORING_RUN_PROFILE": "srp",
    "HEAD_TO_HEAD_CONTEXT_PROFILE": "h2hc",
    "LEAGUE_ZONE_PRESSURE_PROFILE": "lzp",
}


def build_v2107_context_indicator_shadow_mix(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    indicator_results: list[dict[str, Any]] | dict[str, dict[str, Any]],
    weights: dict[str, float] | None = None,
    max_total_shift: float = 0.06,
) -> dict[str, object]:
    return _build_mix("v2107_mix", base_home_probability, base_draw_probability, base_away_probability, indicator_results, weights, max_total_shift, PREFIX_BY_NAME)
