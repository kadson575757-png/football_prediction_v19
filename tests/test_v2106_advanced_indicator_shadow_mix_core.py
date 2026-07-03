from football_prediction_v19.analysis.v2106_advanced_indicator_shadow_mix import build_v2106_advanced_indicator_shadow_mix


def _ind(name, quality="FULL", home=0.45, draw=0.3, away=0.25, applied=True):
    return {
        "indicator_name": name,
        "indicator_quality": quality,
        "adjustment_applied": applied,
        "adjusted_home_win_probability": home,
        "adjusted_draw_probability": draw,
        "adjusted_away_probability": away,
    }


def test_v2106_advanced_indicator_shadow_mix_works_with_one_indicator():
    result = build_v2106_advanced_indicator_shadow_mix(0.4, 0.3, 0.3, [_ind("OPPONENT_ADJUSTED_RECENT_FORM")])

    assert result["v2106_mix_indicator_count"] == 1
    assert result["v2106_mix_total_shift"] <= 0.06
    assert round(result["v2106_mix_adjusted_home_win_probability"] + result["v2106_mix_adjusted_draw_probability"] + result["v2106_mix_adjusted_away_probability"], 6) == 1.0


def test_v2106_advanced_indicator_shadow_mix_combines_shadow_outputs():
    indicators = [
        _ind("OPPONENT_ADJUSTED_RECENT_FORM", home=0.45, draw=0.29, away=0.26),
        _ind("RECENT_GOAL_TREND_PROFILE", home=0.44, draw=0.30, away=0.26),
        _ind("VENUE_RECENT_MOMENTUM_PROFILE", "LOW", home=0.40, draw=0.30, away=0.30, applied=False),
        _ind("RESULT_VOLATILITY_CONSISTENCY_PROFILE", home=0.41, draw=0.32, away=0.27),
    ]

    result = build_v2106_advanced_indicator_shadow_mix(0.4, 0.3, 0.3, indicators)

    assert result["v2106_mix_indicator_count"] == 3
    assert "VENUE_RECENT_MOMENTUM_PROFILE" not in result["v2106_mix_included_indicators"]
    assert "OPPONENT_ADJUSTED_RECENT_FORM" in result["v2106_mix_included_indicators"]
    assert result["v2106_mix_adjusted_home_win_probability"] > 0.4
    assert round(result["v2106_mix_adjusted_home_win_probability"] + result["v2106_mix_adjusted_draw_probability"] + result["v2106_mix_adjusted_away_probability"], 6) == 1.0


def test_v2106_advanced_indicator_shadow_mix_weights_and_max_shift():
    result = build_v2106_advanced_indicator_shadow_mix(
        0.4,
        0.3,
        0.3,
        [_ind("OPPONENT_ADJUSTED_RECENT_FORM", home=0.8, draw=0.1, away=0.1), _ind("RECENT_GOAL_TREND_PROFILE", home=0.2, draw=0.7, away=0.1)],
        weights={"RECENT_GOAL_TREND_PROFILE": 1.0},
        max_total_shift=0.03,
    )

    assert result["v2106_mix_indicator_count"] == 1
    assert result["v2106_mix_total_shift"] <= 0.03
    assert result["v2106_mix_adjusted_draw_probability"] > 0.3
