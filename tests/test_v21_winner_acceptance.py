from football_prediction_v19.analysis.v21_winner_release_gate import run_v21_winner_release_gate


def test_v21_winner_acceptance(tmp_path):
    result = run_v21_winner_release_gate(tmp_path)
    assert result["league_support_status"] == "PASSED"
    assert result["winner_model_status"] == "PASSED"
    assert result["winner_backtest_status"] == "PASSED"
