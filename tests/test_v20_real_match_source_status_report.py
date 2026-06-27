from scripts.run_v20_match import run_v20_match


def test_report_shows_data_blocked_source_status_and_next_fix(tmp_path):
    result = run_v20_match(home_team="Unknown Home", away_team="Unknown Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_one_command_runner", output_dir=tmp_path, base_dir=".")
    text = (tmp_path / "final_match_report.md").read_text(encoding="utf-8")
    assert "# DATA_BLOCKED" in text
    assert "Block Reason:" in text
    assert "Source Status:" in text
    assert "Next Fix:" in text
    assert "football_data" in text
    assert result["staking_logic_enabled"] is False
