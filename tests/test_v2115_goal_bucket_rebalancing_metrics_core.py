import pandas as pd

from football_prediction_v19.analysis.v2115_goal_bucket_rebalancing_test import apply_strategy, compute_strategy_metrics, prepare_rows


def test_v2115_rebalancing_metrics_precision_recall_and_bias():
    rows = prepare_rows(pd.DataFrame([
        {"actual_goal_bucket": "GOALS_2_3", "final_reference_top_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 1},
        {"actual_goal_bucket": "GOALS_4_PLUS", "final_reference_top_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 1},
        {"actual_goal_bucket": "GOALS_4_PLUS", "final_reference_top_goal_bucket": "GOALS_4_PLUS", "final_goal_reference_count": 1},
    ]))
    evaluated = apply_strategy(rows, "BASELINE")
    metrics = compute_strategy_metrics(evaluated, "BASELINE")

    assert metrics["evaluable_count"] == 3
    assert metrics["hit_count"] == 2
    assert metrics["hit_rate"] == 0.6667
    assert metrics["goals_2_3_precision"] == 0.5
    assert metrics["goals_2_3_recall"] == 1.0
    assert metrics["goals_4_plus_precision"] == 1.0
    assert metrics["goals_4_plus_recall"] == 0.5
    assert metrics["prediction_bias_goals_2_3"] == 1

