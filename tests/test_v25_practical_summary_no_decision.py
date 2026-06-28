from football_prediction_v19.analysis.v25_practical_decision_summary import build_practical_decision_summary


def test_v25_practical_summary_no_decision():
    summary = build_practical_decision_summary({"decision_class": "NO_DECISION", "confidence": 0.42})
    assert summary["final_label"] == "No Decision"

