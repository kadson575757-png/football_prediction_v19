import pandas as pd

from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import (
    add_strength_snapshots,
    analyze_match_strategy,
    analyze_team_strength_filtered_patterns,
    choose_final_filtered_reference,
)
from scripts.analyze_v2112_exact_scoreline_pattern_test import _prepare_matches
from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import (
    analyze_exact_scoreline_goal_buckets,
)


def test_v2116_baseline_unfiltered_uses_v2113_goal_bucket_fallback_not_result_tiebreak():
    refs = {
        "exact_pair": pd.DataFrame([
            {"actual_home_goals": 1, "actual_away_goals": 0},
            {"actual_home_goals": 4, "actual_away_goals": 0},
        ]),
        "combined_single": pd.DataFrame([
            {"actual_home_goals": 2, "actual_away_goals": 1},
            {"actual_home_goals": 1, "actual_away_goals": 1},
            {"actual_home_goals": 3, "actual_away_goals": 0},
        ]),
        "home_single": pd.DataFrame(),
        "away_single": pd.DataFrame(),
    }
    final = choose_final_filtered_reference(refs)
    assert final["source"] == "COMBINED_SINGLE"
    assert final["top_goal_bucket"] == "GOALS_2_3"


def test_v2116_baseline_unfiltered_independent_of_strength_quality_and_matches_v2113(tmp_path):
    fixtures = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "A", "away_team": "B", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-02", "home_team": "C", "away_team": "D", "actual_home_goals": 0, "actual_away_goals": 1},
        {"match_date": "2025-08-08", "home_team": "A", "away_team": "C", "actual_home_goals": 1, "actual_away_goals": 0},
        {"match_date": "2025-08-09", "home_team": "B", "away_team": "D", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-16", "home_team": "A", "away_team": "D", "actual_home_goals": 1, "actual_away_goals": 1},
        {"match_date": "2025-08-17", "home_team": "B", "away_team": "C", "actual_home_goals": 0, "actual_away_goals": 3},
    ])
    v2113 = analyze_exact_scoreline_goal_buckets(fixtures, output_dir=tmp_path / "v2113")
    v2116 = analyze_team_strength_filtered_patterns(fixtures, output_dir=tmp_path / "v2116", min_strength_matches=99)
    assert v2116["baseline_goal_bucket_hit_rate"] == v2113["goal_bucket_hit_rate"]

    matches = add_strength_snapshots(_prepare_matches(fixtures, "Premier League", "2025/26"), min_strength_matches=99)
    baseline = analyze_match_strategy(matches, 5, "BASELINE_UNFILTERED")
    matches.loc[:, "strength_quality"] = "LOW"
    matches.loc[:, "home_strength_quality"] = "LOW"
    matches.loc[:, "away_strength_quality"] = "LOW"
    still_baseline = analyze_match_strategy(matches, 5, "BASELINE_UNFILTERED")
    assert still_baseline["final_reference_source"] == baseline["final_reference_source"]
    assert still_baseline["final_reference_count"] == baseline["final_reference_count"]
    assert still_baseline["final_reference_top_goal_bucket"] == baseline["final_reference_top_goal_bucket"]
