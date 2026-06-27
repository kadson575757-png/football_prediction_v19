from football_prediction_v19.analysis.v23_corpus_winner_handoff_gate import run_v23_corpus_winner_handoff_gate


def test_v23_corpus_winner_handoff_safety(tmp_path):
    result = run_v23_corpus_winner_handoff_gate(tmp_path, {"matches_evaluated": 1, "data_blocked_count": 0, "invalid_data_blocked_count": 0, "probabilities_created_count": 1, "decision_attempt_count": 1})
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False

