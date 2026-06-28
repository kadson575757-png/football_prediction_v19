from football_prediction_v19.analysis.v27_evaluation_metrics import compute_v27_metrics


def test_v27_safety_flags_false():
    metrics = compute_v27_metrics(
        [
            {"competition": "A", "decision_class": "WINNER_LEAN", "evaluation_result": "HIT", "result_status": "RESOLVED", "confidence": 0.6},
        ]
    )

    assert metrics["automatic_betting_enabled"] is False
    assert metrics["staking_logic_enabled"] is False
    assert metrics["roi_logic_enabled"] is False
    assert metrics["productive_betting_enabled"] is False
