import pandas as pd

from scripts.analyze_v2114_goal_bucket_bias_diagnostics import compute_confusion_matrix, final_evaluable, prepare_rows


def test_v2114_goal_bucket_confusion_matrix_core():
    rows = prepare_rows(pd.DataFrame([
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 1},
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_4_PLUS", "final_goal_reference_count": 1},
        {"final_reference_top_goal_bucket": "GOALS_4_PLUS", "actual_goal_bucket": "GOALS_0_1", "final_goal_reference_count": 1},
    ]))
    matrix = compute_confusion_matrix(final_evaluable(rows))

    pred_23 = matrix[matrix["predicted_bucket"] == "GOALS_2_3"].iloc[0]
    pred_4p = matrix[matrix["predicted_bucket"] == "GOALS_4_PLUS"].iloc[0]
    assert pred_23["actual_goals_2_3"] == 1
    assert pred_23["actual_goals_4_plus"] == 1
    assert pred_23["total"] == 2
    assert pred_4p["actual_goals_0_1"] == 1

