from scripts.run_v20_real_match_autopilot import run_v20_real_match_autopilot


def test_real_match_autopilot_safety_flags_false(tmp_path):
    result = run_v20_real_match_autopilot(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_real_match_autopilot", output_dir=tmp_path, base_dir=".")
    assert result["network_calls_enabled"] is False
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
