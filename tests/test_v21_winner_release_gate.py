from football_prediction_v19.analysis.v21_winner_release_gate import run_v21_winner_release_gate


def test_v21_winner_release_gate(tmp_path):
    result = run_v21_winner_release_gate(tmp_path)
    assert result["v21_winner_release_gate_status"] == "V21_READY_TO_TAG"
    assert result["recommendation"] == "V21_READY_TO_TAG"
