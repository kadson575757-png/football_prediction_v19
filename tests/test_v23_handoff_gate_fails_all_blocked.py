from football_prediction_v19.analysis.v23_corpus_winner_handoff_gate import run_v23_corpus_winner_handoff_gate


def test_v23_handoff_gate_fails_all_blocked(tmp_path):
    result = run_v23_corpus_winner_handoff_gate(tmp_path, {"matches_evaluated": 10, "data_blocked_count": 10, "invalid_data_blocked_count": 10, "probabilities_created_count": 0, "decision_attempt_count": 0})
    assert result["v23_corpus_winner_handoff_gate_status"] == "V23_NOT_READY"

