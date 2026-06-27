from football_prediction_v19.analysis.v23_corpus_winner_handoff_gate import run_v23_corpus_winner_handoff_gate


def test_v23_corpus_winner_handoff_gate(tmp_path):
    result = run_v23_corpus_winner_handoff_gate(tmp_path, {"matches_evaluated": 10, "data_blocked_count": 0, "invalid_data_blocked_count": 0, "probabilities_created_count": 10, "decision_attempt_count": 10})
    assert result["v23_corpus_winner_handoff_gate_status"] == "V23_READY_TO_TAG"

