import pandas as pd

from scripts.analyze_v2114_goal_bucket_bias_diagnostics import compute_reference_source_performance, final_evaluable, prepare_rows


def test_v2114_reference_source_bucket_performance_core():
    rows = prepare_rows(pd.DataFrame([
        {"final_goal_reference_source": "COMBINED_SINGLE", "final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 1},
        {"final_goal_reference_source": "COMBINED_SINGLE", "final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_4_PLUS", "final_goal_reference_count": 1},
        {"final_goal_reference_source": "EXACT_PAIR", "final_reference_top_goal_bucket": "GOALS_0_1", "actual_goal_bucket": "GOALS_0_1", "final_goal_reference_count": 1},
    ]))
    perf = compute_reference_source_performance(final_evaluable(rows))

    combined = perf[perf["final_goal_reference_source"] == "COMBINED_SINGLE"].iloc[0]
    assert combined["count"] == 2
    assert combined["hit_count"] == 1
    assert combined["hit_rate"] == 0.5
    assert combined["predicted_goals_2_3_count"] == 2
    assert combined["actual_goals_4_plus_count"] == 1

