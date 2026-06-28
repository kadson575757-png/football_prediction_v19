from tests.test_v24_winner_calibration_gate import test_v24_winner_calibration_gate
from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_gate_warns_on_insufficient_corpus(tmp_path):
    test_v24_winner_calibration_gate(tmp_path)
    result = run_v24_winner_calibration_gate(tmp_path / "gate2", tmp_path / "diag", {"matches_requested": 50, "matches_available": 4, "matches_evaluated": 4, "corpus_status": "INSUFFICIENT_SAMPLE", "data_blocked_count": 0, "probabilities_created_count": 4})
    assert result["insufficient_corpus_warning"] is True
    assert result["real_backtest_status"] == "FAILED"

