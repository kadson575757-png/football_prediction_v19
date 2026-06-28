from football_prediction_v19.analysis.v291_ppg_probability_adjustment import apply_home_away_ppg_adjustment


def test_v291_safety_flags_false():
    result = apply_home_away_ppg_adjustment(0.4, 0.3, 0.3, {"indicator_quality": "FULL", "home_away_ppg_diff": 0.8})
    assert "stake" not in result
    assert "roi" not in result
    assert "profit" not in result
