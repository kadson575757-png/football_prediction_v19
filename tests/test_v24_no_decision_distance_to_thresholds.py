from football_prediction_v19.analysis.v24_no_decision_diagnostics import classify_no_decision


def test_v24_no_decision_distance_to_thresholds():
    result = classify_no_decision({"top_edge": 0.02, "confidence": 0.48})
    assert result["distance_to_winner_lean"] > 0
    assert result["distance_to_winner_pick"] > result["distance_to_winner_lean"]

