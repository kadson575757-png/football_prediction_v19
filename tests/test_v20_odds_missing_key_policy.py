from scripts.run_v20_match import run_v20_match


def test_missing_odds_key_with_table_xg_not_data_blocked(monkeypatch, tmp_path):
    monkeypatch.delenv("THE_ODDS_API_KEY", raising=False)
    result = run_v20_match(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_one_command_runner", output_dir=tmp_path, base_dir=".")
    assert result["decision_class"] != "DATA_BLOCKED"
    assert result["missing_data"]["odds"] is False  # mock odds exists
    assert "super_private" not in (tmp_path / "machine_result.json").read_text(encoding="utf-8")
