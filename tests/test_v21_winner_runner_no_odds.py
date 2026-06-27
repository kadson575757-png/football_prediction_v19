from scripts.run_v21_predict_winner import run_v21_predict_winner


def test_v21_winner_runner_no_odds(tmp_path):
    result = run_v21_predict_winner(home_team="Demo Home", away_team="Demo Away", competition="Premier League", season="2025/26", match_date="2026-02-15", mock_data_dir="tests/fixtures/v20_live_source_adapters", output_dir=tmp_path)
    assert result["winner_model"]["automatic_betting_enabled"] is False
    assert result["decision_class"] != "DATA_BLOCKED" or result["eligibility_class"] == "DATA_BLOCKED"
