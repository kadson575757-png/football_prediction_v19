from football_prediction_v19.analysis.v2106_combined_indicator_shadow_mix import build_v2106_combined_indicator_shadow_mix


def _indicator(name, home, draw, away):
    return {
        "indicator_name": name,
        "indicator_quality": "FULL",
        "adjustment_applied": True,
        "adjusted_home_win_probability": home,
        "adjusted_draw_probability": draw,
        "adjusted_away_probability": away,
    }


def test_v2106_combined_indicator_shadow_mix_accepts_prior_and_advanced_indicators():
    indicators = [
        _indicator("DRAW_TENDENCY", 0.39, 0.33, 0.28),
        _indicator("VENUE_RESULT_RATE", 0.43, 0.29, 0.28),
        _indicator("GOAL_MARGIN_PROFILE", 0.42, 0.30, 0.28),
        _indicator("VENUE_SCORING_BALANCE", 0.44, 0.28, 0.28),
        _indicator("CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", 0.41, 0.31, 0.28),
        _indicator("REST_DAYS_CONGESTION_PROFILE", 0.42, 0.30, 0.28),
        _indicator("TABLE_STRENGTH_GAP_PROFILE", 0.45, 0.28, 0.27),
        _indicator("COMEBACK_BLOWN_LEAD_PROFILE", 0.40, 0.32, 0.28),
        _indicator("OPPONENT_ADJUSTED_RECENT_FORM", 0.46, 0.28, 0.26),
        _indicator("RECENT_GOAL_TREND_PROFILE", 0.44, 0.30, 0.26),
        _indicator("VENUE_RECENT_MOMENTUM_PROFILE", 0.43, 0.30, 0.27),
        _indicator("RESULT_VOLATILITY_CONSISTENCY_PROFILE", 0.40, 0.33, 0.27),
    ]

    result = build_v2106_combined_indicator_shadow_mix(0.4, 0.3, 0.3, indicators)

    assert result["v2106_combined_mix_indicator_count"] == 12
    assert "RESULT_VOLATILITY_CONSISTENCY_PROFILE" in result["v2106_combined_mix_included_indicators"]
    assert result["v2106_combined_mix_adjusted_home_win_probability"] > 0.4
    assert round(result["v2106_combined_mix_adjusted_home_win_probability"] + result["v2106_combined_mix_adjusted_draw_probability"] + result["v2106_combined_mix_adjusted_away_probability"], 6) == 1.0


def test_v2106_combined_indicator_shadow_mix_handles_missing_low_and_shift_cap():
    indicators = [
        _indicator("DRAW_TENDENCY", 0.8, 0.1, 0.1),
        {**_indicator("VENUE_RESULT_RATE", 0.9, 0.05, 0.05), "indicator_quality": "LOW"},
        _indicator("OPPONENT_ADJUSTED_RECENT_FORM", 0.2, 0.7, 0.1),
    ]

    result = build_v2106_combined_indicator_shadow_mix(0.4, 0.3, 0.3, indicators, weights={"OPPONENT_ADJUSTED_RECENT_FORM": 1.0}, max_total_shift=0.04)

    assert result["v2106_combined_mix_indicator_count"] == 1
    assert "VENUE_RESULT_RATE" not in result["v2106_combined_mix_included_indicators"]
    assert result["v2106_combined_mix_total_shift"] <= 0.04
    assert result["v2106_combined_mix_adjusted_draw_probability"] > 0.3
