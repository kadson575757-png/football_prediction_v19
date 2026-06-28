from tests.test_v24_winner_calibration_gate import test_v24_winner_calibration_gate
from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_gate_not_ready_when_real_backtest_only_4_matches(tmp_path):
    test_v24_winner_calibration_gate(tmp_path)
    result = run_v24_winner_calibration_gate(tmp_path / "gate2", tmp_path / "diag", {"matches_requested": 50, "matches_available": 4, "matches_evaluated": 4, "data_blocked_count": 0, "probabilities_created_count": 4})
    assert result["v24_winner_calibration_gate_status"] == "V24_NOT_READY"
    assert result["recommendation"] == "BUILD_OR_WARM_V22_CORPUS"

