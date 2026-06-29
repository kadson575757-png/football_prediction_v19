from football_prediction_v19.analysis.v296_goals_for_probability_adjustment import apply_goals_for_shadow_adjustment


def test_v296_positive_goals_for_diff_raises_home_shadow():
    result = apply_goals_for_shadow_adjustment(0.4, 0.3, 0.3, {"goals_for_indicator_quality": "FULL", "goals_for_per_match_diff": 0.5})
    assert result["gf_adjustment_applied"] is True
    assert result["gf_adjusted_home_win_probability"] > 0.4
    assert result["gf_adjusted_away_probability"] < 0.3


def test_v296_negative_goals_for_diff_raises_away_shadow():
    result = apply_goals_for_shadow_adjustment(0.4, 0.3, 0.3, {"goals_for_indicator_quality": "FULL", "goals_for_per_match_diff": -0.5})
    assert result["gf_adjustment_applied"] is True
    assert result["gf_adjusted_away_probability"] > 0.3
    assert result["gf_adjusted_home_win_probability"] < 0.4


def test_v296_low_quality_no_adjustment():
    result = apply_goals_for_shadow_adjustment(0.4, 0.3, 0.3, {"goals_for_indicator_quality": "LOW", "goals_for_per_match_diff": 1.0})
    assert result["gf_adjustment_applied"] is False
    assert result["gf_adjusted_home_win_probability"] == 0.4


def test_v296_shadow_probabilities_sum_to_one():
    result = apply_goals_for_shadow_adjustment(0.42, 0.29, 0.29, {"goals_for_indicator_quality": "FULL", "goals_for_per_match_diff": 0.9})
    total = result["gf_adjusted_home_win_probability"] + result["gf_adjusted_draw_probability"] + result["gf_adjusted_away_probability"]
    assert abs(total - 1.0) < 0.0001
