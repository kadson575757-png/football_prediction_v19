from football_prediction_v19.analysis.v2104_indicator_shadow_mix import build_indicator_shadow_mix


def _indicator(name, quality="FULL", home=0.45, draw=0.3, away=0.25, applied=True):
    return {
        "indicator_name": name,
        "indicator_quality": quality,
        "adjustment_applied": applied,
        "adjusted_home_win_probability": home,
        "adjusted_draw_probability": draw,
        "adjusted_away_probability": away,
    }


def test_v2104_mix_with_one_indicator():
    result = build_indicator_shadow_mix(0.4, 0.3, 0.3, [_indicator("DRAW_TENDENCY", draw=0.36, home=0.37, away=0.27)])

    assert result["mix_indicator_count"] == 1
    assert "DRAW_TENDENCY" in result["mix_included_indicators"]
    assert result["mix_adjusted_draw_probability"] > 0.3


def test_v2104_mix_with_multiple_indicators_and_low_ignored():
    result = build_indicator_shadow_mix(
        0.4,
        0.3,
        0.3,
        [_indicator("DRAW_TENDENCY", draw=0.36, home=0.37, away=0.27), _indicator("VENUE_RESULT_RATE", home=0.46, draw=0.29, away=0.25), _indicator("GOAL_MARGIN_PROFILE", "LOW", home=0.9)],
    )

    assert result["mix_indicator_count"] == 2
    assert "GOAL_MARGIN_PROFILE" not in result["mix_included_indicators"]
    assert round(result["mix_adjusted_home_win_probability"] + result["mix_adjusted_draw_probability"] + result["mix_adjusted_away_probability"], 4) == 1.0


def test_v2104_mix_weights_and_max_shift():
    result = build_indicator_shadow_mix(
        0.4,
        0.3,
        0.3,
        [_indicator("DRAW_TENDENCY", home=0.2, draw=0.7, away=0.1), _indicator("VENUE_RESULT_RATE", home=0.8, draw=0.1, away=0.1)],
        weights={"DRAW_TENDENCY": 1.0},
        max_total_shift=0.03,
    )

    assert result["mix_indicator_count"] == 1
    assert result["mix_total_shift"] <= 0.03
    assert result["mix_adjusted_draw_probability"] > 0.3
