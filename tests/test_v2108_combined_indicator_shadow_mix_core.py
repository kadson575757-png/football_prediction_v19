from football_prediction_v19.analysis.v2108_combined_indicator_shadow_mix import build_v2108_combined_indicator_shadow_mix


def _indicator(name, home=0.44, draw=0.3, away=0.26, quality="FULL", applied=True):
    return {"indicator_name": name, "indicator_quality": quality, "adjustment_applied": applied, "adjusted_home_win_probability": home, "adjusted_draw_probability": draw, "adjusted_away_probability": away}


def test_v2108_combined_mix_accepts_all_generations():
    names = [
        "DRAW_TENDENCY", "VENUE_RESULT_RATE", "GOAL_MARGIN_PROFILE", "VENUE_SCORING_BALANCE",
        "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", "REST_DAYS_CONGESTION_PROFILE", "TABLE_STRENGTH_GAP_PROFILE", "COMEBACK_BLOWN_LEAD_PROFILE",
        "OPPONENT_ADJUSTED_RECENT_FORM", "RECENT_GOAL_TREND_PROFILE", "VENUE_RECENT_MOMENTUM_PROFILE", "RESULT_VOLATILITY_CONSISTENCY_PROFILE",
        "RESULT_STREAK_PROFILE", "SCORING_RUN_PROFILE", "HEAD_TO_HEAD_CONTEXT_PROFILE", "LEAGUE_ZONE_PRESSURE_PROFILE",
        "COMMON_OPPONENT_PERFORMANCE_PROFILE", "STRENGTH_BAND_PERFORMANCE_PROFILE", "RESPONSE_AFTER_RESULT_PROFILE", "HEAVY_RESULT_EXPOSURE_PROFILE",
    ]
    result = build_v2108_combined_indicator_shadow_mix(0.4, 0.3, 0.3, [_indicator(name) for name in names])

    assert result["v2108_combined_mix_indicator_count"] == 20
    assert "HEAVY_RESULT_EXPOSURE_PROFILE" in result["v2108_combined_mix_included_indicators"]
    assert round(result["v2108_combined_mix_adjusted_home_win_probability"] + result["v2108_combined_mix_adjusted_draw_probability"] + result["v2108_combined_mix_adjusted_away_probability"], 6) == 1.0


def test_v2108_combined_mix_missing_low_and_shift_cap():
    result = build_v2108_combined_indicator_shadow_mix(0.4, 0.3, 0.3, [_indicator("DRAW_TENDENCY", home=0.9), _indicator("COMMON_OPPONENT_PERFORMANCE_PROFILE", quality="LOW", home=0.9), _indicator("STRENGTH_BAND_PERFORMANCE_PROFILE", home=0.2, draw=0.7)], weights={"STRENGTH_BAND_PERFORMANCE_PROFILE": 1.0}, max_total_shift=0.04)

    assert result["v2108_combined_mix_indicator_count"] == 1
    assert "COMMON_OPPONENT_PERFORMANCE_PROFILE" not in result["v2108_combined_mix_included_indicators"]
    assert result["v2108_combined_mix_total_shift"] <= 0.04
