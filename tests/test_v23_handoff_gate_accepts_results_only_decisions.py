from tests.v23_test_helpers import run_results_only_backtest
from football_prediction_v19.analysis.v23_corpus_winner_handoff_gate import run_v23_corpus_winner_handoff_gate


def test_v23_handoff_gate_accepts_results_only_decisions(tmp_path):
    metrics = run_results_only_backtest(tmp_path / "bt")
    result = run_v23_corpus_winner_handoff_gate(tmp_path / "gate", metrics)
    assert result["partial_model_status"] == "PASSED"
    assert result["backtest_blocking_status"] == "PASSED"

