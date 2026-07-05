import pandas as pd

from football_prediction_v19.analysis.v2115_goal_bucket_rebalancing_test import apply_strategy, prepare_rows


def test_v2115_rebalancing_strategies_choose_expected_buckets():
    rows = prepare_rows(pd.DataFrame([{
        "actual_goal_bucket": "GOALS_4_PLUS",
        "final_reference_top_goal_bucket": "GOALS_2_3",
        "final_goal_reference_count": 7,
        "final_reference_goals_0_1_rate": 0.10,
        "final_reference_goals_2_3_rate": 0.36,
        "final_reference_goals_4_plus_rate": 0.34,
        "combined_single_top_goal_bucket": "GOALS_4_PLUS",
        "combined_single_goal_reference_count": 7,
        "away_single_top_goal_bucket": "GOALS_0_1",
    }]))

    assert apply_strategy(rows, "BASELINE").loc[0, "strategy_predicted_goal_bucket"] == "GOALS_2_3"
    assert apply_strategy(rows, "REFERENCE_COUNT_FILTER").loc[0, "strategy_predicted_goal_bucket"] == "GOALS_2_3"
    assert apply_strategy(rows, "STRONG_BUCKET_EDGE").loc[0, "strategy_predicted_goal_bucket"] == "NO_CLEAR_TOP"
    assert apply_strategy(rows, "EXTREME_BUCKET_BOOST").loc[0, "strategy_predicted_goal_bucket"] == "GOALS_4_PLUS"
    assert apply_strategy(rows, "COMBINED_SINGLE_ONLY").loc[0, "strategy_predicted_goal_bucket"] == "GOALS_4_PLUS"
    assert apply_strategy(rows, "AWAY_SINGLE_ONLY").loc[0, "strategy_predicted_goal_bucket"] == "GOALS_0_1"
    assert apply_strategy(rows, "COMBINED_SINGLE_WITH_REF_6_10").loc[0, "strategy_predicted_goal_bucket"] == "GOALS_4_PLUS"


def test_v2115_reference_count_filter_blocks_outside_range():
    rows = prepare_rows(pd.DataFrame([{"actual_goal_bucket": "GOALS_2_3", "final_reference_top_goal_bucket": "GOALS_2_3", "final_goal_reference_count": 3}]))

    assert apply_strategy(rows, "REFERENCE_COUNT_FILTER").loc[0, "strategy_predicted_goal_bucket"] == "NO_CLEAR_TOP"
