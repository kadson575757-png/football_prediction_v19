from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_calibration_safety(tmp_path):
    result = run_v24_winner_calibration_gate(tmp_path / "gate", tmp_path / "missing", {"matches_evaluated": 0})
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
