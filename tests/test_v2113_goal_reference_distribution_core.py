import pandas as pd

from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import goal_reference_stats


def test_v2113_goal_reference_distribution_stats_and_no_clear_top():
    rows = pd.DataFrame([
        {"actual_home_goals": 1, "actual_away_goals": 0},
        {"actual_home_goals": 2, "actual_away_goals": 0},
        {"actual_home_goals": 3, "actual_away_goals": 1},
        {"actual_home_goals": 2, "actual_away_goals": 2},
    ])

    stats = goal_reference_stats(rows)

    assert stats["goal_reference_count"] == 4
    assert stats["goals_0_1_count"] == 1
    assert stats["goals_2_3_count"] == 1
    assert stats["goals_4_plus_count"] == 2
    assert stats["top_goal_bucket"] == "GOALS_4_PLUS"
    assert stats["average_total_goals"] == 2.75
    assert stats["median_total_goals"] == 3.0
    assert stats["most_common_total_goals"] == 4

    tied = goal_reference_stats(pd.DataFrame([
        {"actual_home_goals": 1, "actual_away_goals": 0},
        {"actual_home_goals": 2, "actual_away_goals": 0},
        {"actual_home_goals": 3, "actual_away_goals": 1},
    ]))
    assert tied["top_goal_bucket"] == "NO_CLEAR_TOP"

