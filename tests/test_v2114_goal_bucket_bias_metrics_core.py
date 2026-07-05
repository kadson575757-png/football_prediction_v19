import pandas as pd

from scripts.analyze_v2114_goal_bucket_bias_diagnostics import compute_bias_metrics, final_evaluable, prepare_rows


def test_v2114_goal_bucket_bias_metrics_core():
    rows = prepare_rows(pd.DataFrame([
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_0_1", "final_goal_reference_count": 1},
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 1},
        {"final_reference_top_goal_bucket": "GOALS_4_PLUS", "actual_goal_bucket": "GOALS_0_1", "final_goal_reference_count": 1},
    ]))
    bias = compute_bias_metrics(final_evaluable(rows))

    assert bias["predicted_goals_2_3_count"] == 2
    assert bias["actual_goals_0_1_count"] == 2
    assert bias["goals_2_3_prediction_bias"] == 1
    assert bias["goals_0_1_prediction_bias"] == -2
    assert bias["goals_2_3_prediction_bias_rate"] == 0.3334
