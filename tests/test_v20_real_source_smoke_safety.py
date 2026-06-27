from football_prediction_v19.analysis.v20_real_source_smoke_suite import run_real_source_smoke_suite


def test_real_source_smoke_safety_flags_false(tmp_path):
    result = run_real_source_smoke_suite(tmp_path, enable_network=True)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
