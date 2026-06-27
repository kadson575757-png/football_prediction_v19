from football_prediction_v19.analysis.v20_model_policy_calibrator import calibrate_v20_model_policy


def test_model_policy_calibrator_writes_thresholds(tmp_path):
    result = calibrate_v20_model_policy(tmp_path)
    assert result["v20_model_policy_calibration_status"] == "READY"
    assert (tmp_path / "v20_model_policy_thresholds.json").exists()
