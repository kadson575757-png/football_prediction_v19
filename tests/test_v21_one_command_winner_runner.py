from scripts.run_v21_predict_winner import run_v21_predict_winner


def test_v21_one_command_winner_runner(tmp_path):
    result = run_v21_predict_winner(home_team="Demo Home", away_team="Demo Away", competition="Premier League", season="2025/26", match_date="2026-02-15", mock_data_dir="tests/fixtures/v20_live_source_adapters", output_dir=tmp_path)
    assert result["v21_winner_prediction_status"] in {"READY", "PARTIAL", "BLOCKED"}
    assert result["decision_class"] in {"WINNER_PICK", "WINNER_LEAN", "NO_CLEAR_WINNER", "NO_DECISION", "DATA_BLOCKED"}
    assert result["automatic_betting_enabled"] is False
