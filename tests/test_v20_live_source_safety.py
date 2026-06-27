from scripts.run_v20_historical_internet_prediction import run_v20_historical_internet_prediction


def test_live_source_safety_flags_false_and_no_secrets_in_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "super_private_v20_key")
    result = run_v20_historical_internet_prediction(
        home_team="Demo Home",
        away_team="Demo Away",
        competition="Demo League",
        season="2025/26",
        match_date="2026-02-14",
        cutoff_policy="MATCH_DATE_START",
        mock_data_dir="tests/fixtures/v20_live_source_adapters",
        source_profile="config/v20_internet_sources.yaml",
        output_dir=tmp_path / "out",
        base_dir=".",
    )
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    combined = "\n".join(p.read_text(encoding="utf-8") for p in (tmp_path / "out").glob("*.json"))
    assert "super_private_v20_key" not in combined
