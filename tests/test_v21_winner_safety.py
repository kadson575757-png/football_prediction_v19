from football_prediction_v19.analysis.v21_winner_release_gate import run_v21_winner_release_gate


def test_v21_winner_safety(tmp_path):
    result = run_v21_winner_release_gate(tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
