from football_prediction_v19.analysis.v20_model_policy_calibrator import calibrate_v20_model_policy


def test_model_policy_safety_flags_false(tmp_path):
    result = calibrate_v20_model_policy(tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
