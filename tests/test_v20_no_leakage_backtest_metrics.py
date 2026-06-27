from football_prediction_v19.analysis.v20_no_leakage_backtest_metrics import calibration_bins, compute_backtest_metrics


def test_no_leakage_backtest_metrics_no_financial_outputs():
    metrics = compute_backtest_metrics([{"decision_class": "MODEL_TIP", "actual_result": "HOME", "home_probability": 0.6, "draw_probability": 0.2, "away_probability": 0.2, "confidence": 0.7}])
    assert metrics["matches_evaluated"] == 1
    assert "roi" not in metrics
    assert calibration_bins([{"confidence": 0.74}])[0]["confidence_bin"] == "0.7"
