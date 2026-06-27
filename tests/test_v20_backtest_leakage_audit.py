from football_prediction_v19.analysis.v20_backtest_leakage_audit import write_backtest_leakage_audit


def test_backtest_leakage_audit_counts_blocked(tmp_path):
    result = write_backtest_leakage_audit([{"match_id": "m1", "leakage_status": "BLOCKED", "analysis_cutoff": "x"}], tmp_path)
    assert result["leakage_blocked_count"] == 1
    assert (tmp_path / "v20_backtest_leakage_audit.csv").exists()
