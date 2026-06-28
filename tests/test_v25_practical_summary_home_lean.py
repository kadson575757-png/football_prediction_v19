from football_prediction_v19.analysis.v25_practical_decision_summary import build_practical_decision_summary


def test_v25_practical_summary_home_lean():
    summary = build_practical_decision_summary({"decision_class": "WINNER_LEAN", "predicted_winner": "HOME", "home_team": "Arsenal", "confidence": 0.58, "xg_available": False})
    assert summary["final_label"] == "Home Lean"
    assert "Arsenal" in summary["short_reason"]

