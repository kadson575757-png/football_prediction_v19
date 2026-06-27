from football_prediction_v19.analysis.v20_backtest_report import write_backtest_report


def test_backtest_report_contains_no_roi_safety(tmp_path):
    text = open(write_backtest_report({"matches_total": 1, "matches_evaluated": 1, "accuracy_1x2": 1, "brier_score": 0.1}, tmp_path), encoding="utf-8").read()
    assert "No ROI" in text
    assert "No stake" in text
