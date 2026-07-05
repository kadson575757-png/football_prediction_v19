import pandas as pd

from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import compute_goal_bucket_summary


def test_v2113_goal_bucket_hit_rate_excludes_no_reference_and_no_clear_top(tmp_path):
    rows = pd.DataFrame([
        {
            "actual_goal_bucket": "GOALS_2_3",
            "final_reference_top_goal_bucket": "GOALS_2_3",
            "final_goal_reference_count": 2,
            "goal_bucket_hit": True,
            "exact_total_goals_hit": True,
            "exact_pair_goal_reference_count": 1,
            "exact_pair_top_goal_bucket": "GOALS_2_3",
            "combined_single_goal_reference_count": 1,
            "combined_single_top_goal_bucket": "GOALS_4_PLUS",
            "home_single_goal_reference_count": 1,
            "home_single_top_goal_bucket": "GOALS_2_3",
            "away_single_goal_reference_count": 0,
            "away_single_top_goal_bucket": "NO_REFERENCE",
        },
        {
            "actual_goal_bucket": "GOALS_4_PLUS",
            "final_reference_top_goal_bucket": "GOALS_2_3",
            "final_goal_reference_count": 2,
            "goal_bucket_hit": False,
            "exact_total_goals_hit": False,
            "exact_pair_goal_reference_count": 0,
            "exact_pair_top_goal_bucket": "NO_REFERENCE",
            "combined_single_goal_reference_count": 1,
            "combined_single_top_goal_bucket": "GOALS_4_PLUS",
            "home_single_goal_reference_count": 1,
            "home_single_top_goal_bucket": "GOALS_0_1",
            "away_single_goal_reference_count": 1,
            "away_single_top_goal_bucket": "GOALS_4_PLUS",
        },
        {
            "actual_goal_bucket": "GOALS_0_1",
            "final_reference_top_goal_bucket": "NO_REFERENCE",
            "final_goal_reference_count": 0,
            "goal_bucket_hit": "",
            "exact_total_goals_hit": "",
            "exact_pair_goal_reference_count": 0,
            "exact_pair_top_goal_bucket": "NO_REFERENCE",
            "combined_single_goal_reference_count": 0,
            "combined_single_top_goal_bucket": "NO_REFERENCE",
            "home_single_goal_reference_count": 0,
            "home_single_top_goal_bucket": "NO_REFERENCE",
            "away_single_goal_reference_count": 0,
            "away_single_top_goal_bucket": "NO_REFERENCE",
        },
        {
            "actual_goal_bucket": "GOALS_4_PLUS",
            "final_reference_top_goal_bucket": "NO_CLEAR_TOP",
            "final_goal_reference_count": 2,
            "goal_bucket_hit": "",
            "exact_total_goals_hit": "",
            "exact_pair_goal_reference_count": 1,
            "exact_pair_top_goal_bucket": "NO_CLEAR_TOP",
            "combined_single_goal_reference_count": 1,
            "combined_single_top_goal_bucket": "NO_CLEAR_TOP",
            "home_single_goal_reference_count": 1,
            "home_single_top_goal_bucket": "NO_CLEAR_TOP",
            "away_single_goal_reference_count": 1,
            "away_single_top_goal_bucket": "NO_CLEAR_TOP",
        },
    ])

    summary = compute_goal_bucket_summary(rows, fixtures_loaded=4, competition="Premier League", season="2025/26", output_dir=tmp_path)

    assert summary["goal_bucket_evaluable_count"] == 2
    assert summary["goal_bucket_hit_count"] == 1
    assert summary["goal_bucket_miss_count"] == 1
    assert summary["goal_bucket_hit_rate"] == 0.5
    assert summary["goal_bucket_no_reference_count"] == 1
    assert summary["goal_bucket_no_clear_top_count"] == 1
    assert summary["exact_pair_goal_bucket_evaluable_count"] == 1
    assert summary["exact_pair_goal_bucket_hit_rate"] == 1.0
    assert summary["combined_single_goal_bucket_evaluable_count"] == 2
    assert summary["combined_single_goal_bucket_hit_rate"] == 0.5
    assert summary["home_single_goal_bucket_evaluable_count"] == 2
    assert summary["home_single_goal_bucket_hit_rate"] == 0.5
    assert summary["away_single_goal_bucket_evaluable_count"] == 1
    assert summary["away_single_goal_bucket_hit_rate"] == 1.0
    assert summary["exact_total_goals_evaluable_count"] == 2
    assert summary["exact_total_goals_hit_rate"] == 0.5

