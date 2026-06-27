from tests.v23_test_helpers import run_results_only_backtest


def test_v23_backtest_dashboard_has_handoff_metrics(tmp_path):
    run_results_only_backtest(tmp_path)
    text = (tmp_path / "out" / "winner_backtest_dashboard.md").read_text(encoding="utf-8")
    assert "model_ran_count" in text
    assert "probabilities_created_count" in text
    assert "decision_attempt_count" in text

