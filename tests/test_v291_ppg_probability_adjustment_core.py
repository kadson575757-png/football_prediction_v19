from football_prediction_v19.analysis.v291_ppg_probability_adjustment import apply_home_away_ppg_adjustment


def test_v291_positive_ppg_diff_raises_home_slightly():
    result = apply_home_away_ppg_adjustment(0.4, 0.3, 0.3, {"indicator_quality": "FULL", "home_away_ppg_diff": 0.8})
    assert result["ppg_adjustment_applied"] is True
    assert result["adjusted_home_win_probability"] > result["base_home_win_probability"]
    assert result["adjusted_away_win_probability"] < result["base_away_probability"]


def test_v291_negative_ppg_diff_raises_away_slightly():
    result = apply_home_away_ppg_adjustment(0.4, 0.3, 0.3, {"indicator_quality": "FULL", "home_away_ppg_diff": -0.8})
    assert result["ppg_adjustment_applied"] is True
    assert result["adjusted_away_win_probability"] > result["base_away_probability"]
    assert result["adjusted_home_win_probability"] < result["base_home_win_probability"]


def test_v291_low_quality_no_adjustment():
    result = apply_home_away_ppg_adjustment(0.4, 0.3, 0.3, {"indicator_quality": "LOW", "home_away_ppg_diff": 2.0})
    assert result["ppg_adjustment_applied"] is False
    assert result["adjusted_home_win_probability"] == 0.4


def test_v291_adjusted_probabilities_sum_to_one():
    result = apply_home_away_ppg_adjustment(0.42, 0.29, 0.29, {"indicator_quality": "FULL", "home_away_ppg_diff": 1.4})
    total = result["adjusted_home_win_probability"] + result["adjusted_draw_probability"] + result["adjusted_away_win_probability"]
    assert abs(total - 1.0) < 0.0001

