from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_calibration_gate_fails_missing_diagnostics(tmp_path):
    result = run_v24_winner_calibration_gate(tmp_path / "gate", tmp_path / "missing", {"matches_evaluated": 3, "data_blocked_count": 0, "probabilities_created_count": 3})
    assert result["v24_winner_calibration_gate_status"] == "V24_NOT_READY"

