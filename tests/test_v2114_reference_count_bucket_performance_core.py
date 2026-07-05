import pandas as pd

from scripts.analyze_v2114_goal_bucket_bias_diagnostics import compute_reference_count_performance, final_evaluable, prepare_rows, reference_count_bucket


def test_v2114_reference_count_bucket_performance_core():
    assert reference_count_bucket(1) == "REF_1"
    assert reference_count_bucket(2) == "REF_2"
    assert reference_count_bucket(5) == "REF_3_5"
    assert reference_count_bucket(10) == "REF_6_10"
    assert reference_count_bucket(11) == "REF_11_PLUS"

    rows = prepare_rows(pd.DataFrame([
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 1},
        {"final_reference_top_goal_bucket": "GOALS_2_3", "actual_goal_bucket": "GOALS_4_PLUS", "final_goal_reference_count": 2},
        {"final_reference_top_goal_bucket": "GOALS_4_PLUS", "actual_goal_bucket": "GOALS_4_PLUS", "final_goal_reference_count": 6},
    ]))
    perf = compute_reference_count_performance(final_evaluable(rows))

    ref1 = perf[perf["reference_count_bucket"] == "REF_1"].iloc[0]
    ref2 = perf[perf["reference_count_bucket"] == "REF_2"].iloc[0]
    ref610 = perf[perf["reference_count_bucket"] == "REF_6_10"].iloc[0]
    assert ref1["hit_rate"] == 1.0
    assert ref2["hit_rate"] == 0.0
    assert ref610["hit_rate"] == 1.0

