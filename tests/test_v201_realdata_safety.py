from football_prediction_v19.analysis.v201_realdata_release_gate import run_v201_realdata_release_gate


def test_v201_release_gate_has_no_betting_staking_roi(tmp_path):
    result = run_v201_realdata_release_gate(tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert result["secrets_required"] is False
