from scripts.run_v20_match import run_v20_match


def test_one_command_match_runner_safety(tmp_path):
    result = run_v20_match(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_one_command_runner", output_dir=tmp_path, base_dir=".")
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
