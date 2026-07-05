import pandas as pd

from scripts.analyze_v2114_goal_bucket_bias_diagnostics import compute_bucket_metrics, final_evaluable, prepare_rows


def test_v2114_goal_bucket_precision_recall_and_zero_division():
    rows = prepare_rows(pd.DataFrame([
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 1},
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_4_PLUS", "final_goal_reference_count": 1},
        {"final_reference_top_goal_bucket": "GOALS_4_PLUS", "actual_goal_bucket": "GOALS_4_PLUS", "final_goal_reference_count": 1},
    ]))
    metrics = compute_bucket_metrics(final_evaluable(rows))

    goals_23 = metrics[metrics["bucket"] == "GOALS_2_3"].iloc[0]
    goals_01 = metrics[metrics["bucket"] == "GOALS_0_1"].iloc[0]
    assert goals_23["precision"] == 0.5
    assert goals_23["recall"] == 1.0
    assert round(goals_23["f1_score"], 4) == 0.6667
    assert goals_01["precision"] == 0.0
    assert goals_01["recall"] == 0.0
    assert goals_01["f1_score"] == 0.0

