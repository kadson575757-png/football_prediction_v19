from football_prediction_v19.analysis.v292_last5_probability_adjustment import apply_last5_form_shadow_adjustment


def test_v292_positive_last5_diff_raises_home_shadow():
    result = apply_last5_form_shadow_adjustment(0.4, 0.3, 0.3, {"last5_indicator_quality": "FULL", "last5_points_diff": 6})
    assert result["last5_adjustment_applied"] is True
    assert result["last5_adjusted_home_win_probability"] > 0.4
    assert result["last5_adjusted_away_probability"] < 0.3


def test_v292_negative_last5_diff_raises_away_shadow():
    result = apply_last5_form_shadow_adjustment(0.4, 0.3, 0.3, {"last5_indicator_quality": "FULL", "last5_points_diff": -6})
    assert result["last5_adjustment_applied"] is True
    assert result["last5_adjusted_away_probability"] > 0.3
    assert result["last5_adjusted_home_win_probability"] < 0.4


def test_v292_low_quality_no_adjustment():
    result = apply_last5_form_shadow_adjustment(0.4, 0.3, 0.3, {"last5_indicator_quality": "LOW", "last5_points_diff": 9})
    assert result["last5_adjustment_applied"] is False
    assert result["last5_adjusted_home_win_probability"] == 0.4


def test_v292_shadow_probabilities_sum_to_one():
    result = apply_last5_form_shadow_adjustment(0.42, 0.29, 0.29, {"last5_indicator_quality": "FULL", "last5_points_diff": 10})
    total = result["last5_adjusted_home_win_probability"] + result["last5_adjusted_draw_probability"] + result["last5_adjusted_away_probability"]
    assert abs(total - 1.0) < 0.0001
