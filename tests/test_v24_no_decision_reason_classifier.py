from football_prediction_v19.analysis.v24_no_decision_diagnostics import classify_no_decision


def test_v24_no_decision_reason_classifier():
    result = classify_no_decision({"top_edge": 0.01, "confidence": 0.4, "source_quality_band": "LOW", "top_probability": 0.35, "draw_probability": 0.34, "odds_available": False})
    assert result["primary_reason"] in {"EDGE_TOO_SMALL", "CONFIDENCE_TOO_LOW", "SOURCE_QUALITY_TOO_LOW"}

