from scripts.run_v20_match import run_v20_match


def test_one_command_match_runner_mock(tmp_path):
    result = run_v20_match(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_one_command_runner", output_dir=tmp_path, base_dir=".")
    assert result["v20_match_status"] in {"READY", "PARTIAL"}
    assert result["decision_class"] in {"MODEL_TIP", "ANALYST_LEAN", "NO_BET", "DATA_BLOCKED"}
    assert (tmp_path / "machine_result.json").exists()
