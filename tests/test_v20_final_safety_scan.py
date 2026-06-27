from football_prediction_v19.analysis.v20_final_safety_scan import run_v20_final_safety_scan


def test_final_safety_scan_passes():
    result = run_v20_final_safety_scan(".")
    assert result["safety_scan_status"] == "PASSED"
    assert result["automatic_betting_enabled"] is False
