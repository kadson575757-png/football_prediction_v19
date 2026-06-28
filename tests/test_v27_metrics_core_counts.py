from football_prediction_v19.analysis.v27_evaluation_metrics import compute_v27_metrics


def test_v27_metrics_core_counts():
    rows = [
        {"competition": "A", "decision_class": "WINNER_LEAN", "evaluation_result": "HIT", "result_status": "RESOLVED", "confidence": 0.6, "risk_notes": "ok"},
        {"competition": "A", "decision_class": "WINNER_PICK", "evaluation_result": "MISS", "result_status": "RESOLVED", "confidence": 0.7, "risk_notes": "risk"},
        {"competition": "B", "decision_class": "NO_DECISION", "evaluation_result": "NO_DECISION", "result_status": "RESOLVED", "confidence": 0.1, "risk_notes": "no clear"},
        {"competition": "B", "decision_class": "DATA_BLOCKED", "evaluation_result": "DATA_BLOCKED", "result_status": "NOT_FOUND", "confidence": 0.0, "block_reason_text": "blocked"},
        {"competition": "C", "decision_class": "WINNER_LEAN", "evaluation_result": "RESULT_UNKNOWN", "result_status": "NOT_FOUND", "confidence": 0.5, "risk_notes": "unknown"},
    ]

    metrics = compute_v27_metrics(rows)

    assert metrics["hit_count"] == 1
    assert metrics["miss_count"] == 1
    assert metrics["no_decision_count"] == 1
    assert metrics["data_blocked_count"] == 1
    assert metrics["result_unknown_count"] == 1
    forbidden = {"roi", "profit", "yield", "stake", "bankroll", "odds_performance"}
    allowed_safety_flags = {"roi_logic_enabled", "staking_logic_enabled"}
    assert not any(key.lower() in forbidden for key in metrics)
    assert not any(word in key.lower() and key not in allowed_safety_flags for key in metrics for word in forbidden)
