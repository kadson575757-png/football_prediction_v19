from football_prediction_v19.analysis.v20_real_source_smoke_suite import run_real_source_smoke_suite


def test_real_source_smoke_suite_manual_network_only(tmp_path):
    result = run_real_source_smoke_suite(tmp_path, enable_network=False)
    assert result["v20_real_source_smoke_status"] == "BLOCKED"
    assert result["network_calls_enabled"] is False
