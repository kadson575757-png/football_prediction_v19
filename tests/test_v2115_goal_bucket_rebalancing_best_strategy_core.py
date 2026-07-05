import pandas as pd

from football_prediction_v19.analysis.v2115_goal_bucket_rebalancing_test import choose_best_strategy


def test_v2115_best_strategy_tie_breakers():
    summary = pd.DataFrame([
        {"strategy_name": "A", "hit_rate": 0.6, "evaluable_count": 10, "prediction_bias_goals_2_3": 5},
        {"strategy_name": "B", "hit_rate": 0.7, "evaluable_count": 5, "prediction_bias_goals_2_3": 1},
        {"strategy_name": "C", "hit_rate": 0.7, "evaluable_count": 8, "prediction_bias_goals_2_3": 4},
        {"strategy_name": "D", "hit_rate": 0.7, "evaluable_count": 8, "prediction_bias_goals_2_3": 2},
    ])

    assert choose_best_strategy(summary)["strategy_name"] == "D"

