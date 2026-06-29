from football_prediction_v19.analysis.v297_goals_against_probability_adjustment import apply_goals_against_shadow_adjustment


def test_v297_positive_goals_against_advantage_diff_raises_home_shadow():
    result = apply_goals_against_shadow_adjustment(0.4, 0.3, 0.3, {"goals_against_indicator_quality": "FULL", "goals_against_advantage_diff": 0.5})
    assert result["ga_adjustment_applied"] is True
    assert result["ga_adjusted_home_win_probability"] > 0.4
    assert result["ga_adjusted_away_probability"] < 0.3


def test_v297_negative_goals_against_advantage_diff_raises_away_shadow():
    result = apply_goals_against_shadow_adjustment(0.4, 0.3, 0.3, {"goals_against_indicator_quality": "FULL", "goals_against_advantage_diff": -0.5})
    assert result["ga_adjustment_applied"] is True
    assert result["ga_adjusted_away_probability"] > 0.3
    assert result["ga_adjusted_home_win_probability"] < 0.4


def test_v297_low_quality_no_adjustment():
    result = apply_goals_against_shadow_adjustment(0.4, 0.3, 0.3, {"goals_against_indicator_quality": "LOW", "goals_against_advantage_diff": 1.0})
    assert result["ga_adjustment_applied"] is False
    assert result["ga_adjusted_home_win_probability"] == 0.4


def test_v297_shadow_probabilities_sum_to_one():
    result = apply_goals_against_shadow_adjustment(0.42, 0.29, 0.29, {"goals_against_indicator_quality": "FULL", "goals_against_advantage_diff": 0.9})
    total = result["ga_adjusted_home_win_probability"] + result["ga_adjusted_draw_probability"] + result["ga_adjusted_away_probability"]
    assert abs(total - 1.0) < 0.0001
