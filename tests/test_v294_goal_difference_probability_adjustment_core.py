from football_prediction_v19.analysis.v294_goal_difference_probability_adjustment import apply_goal_difference_shadow_adjustment


def test_v294_positive_gd_diff_raises_home_shadow():
    result = apply_goal_difference_shadow_adjustment(0.4, 0.3, 0.3, {"goal_difference_indicator_quality": "FULL", "goal_difference_diff": 12})
    assert result["gd_adjustment_applied"] is True
    assert result["gd_adjusted_home_win_probability"] > 0.4
    assert result["gd_adjusted_away_probability"] < 0.3


def test_v294_negative_gd_diff_raises_away_shadow():
    result = apply_goal_difference_shadow_adjustment(0.4, 0.3, 0.3, {"goal_difference_indicator_quality": "FULL", "goal_difference_diff": -12})
    assert result["gd_adjustment_applied"] is True
    assert result["gd_adjusted_away_probability"] > 0.3
    assert result["gd_adjusted_home_win_probability"] < 0.4


def test_v294_low_quality_no_adjustment():
    result = apply_goal_difference_shadow_adjustment(0.4, 0.3, 0.3, {"goal_difference_indicator_quality": "LOW", "goal_difference_diff": 20})
    assert result["gd_adjustment_applied"] is False
    assert result["gd_adjusted_home_win_probability"] == 0.4


def test_v294_shadow_probabilities_sum_to_one():
    result = apply_goal_difference_shadow_adjustment(0.42, 0.29, 0.29, {"goal_difference_indicator_quality": "FULL", "goal_difference_diff": 25})
    total = result["gd_adjusted_home_win_probability"] + result["gd_adjusted_draw_probability"] + result["gd_adjusted_away_probability"]
    assert abs(total - 1.0) < 0.0001
