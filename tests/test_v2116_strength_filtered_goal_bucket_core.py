import pandas as pd

from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import (
    add_strength_snapshots,
    analyze_match_strategy,
    find_pattern_reference_rows,
)
from scripts.analyze_v2112_exact_scoreline_pattern_test import _prepare_matches


def _fixtures():
    return pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "A", "away_team": "B", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-02", "home_team": "C", "away_team": "D", "actual_home_goals": 0, "actual_away_goals": 1},
        {"match_date": "2025-08-08", "home_team": "A", "away_team": "C", "actual_home_goals": 1, "actual_away_goals": 0},
        {"match_date": "2025-08-09", "home_team": "B", "away_team": "D", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-16", "home_team": "A", "away_team": "D", "actual_home_goals": 1, "actual_away_goals": 1},
        {"match_date": "2025-08-17", "home_team": "B", "away_team": "C", "actual_home_goals": 0, "actual_away_goals": 3},
    ])


def test_v2116_pattern_references_first_then_strength_filter_can_remove_all():
    matches = add_strength_snapshots(_prepare_matches(_fixtures(), "Premier League", "2025/26"), min_strength_matches=1)
    idx = 5
    refs = find_pattern_reference_rows(matches, idx, "W 2:0", "L 0:1")
    assert len(refs["away_single"]) > 0

    row = analyze_match_strategy(matches, idx, "STRENGTH_STRICT", home_strength_tolerance=0.0, away_strength_tolerance=0.0, gap_strength_tolerance=0.0)
    assert row["final_reference_top_goal_bucket"] in {"NO_REFERENCE", "NO_CLEAR_TOP"}
    assert row["goal_bucket_hit"] == ""


def test_v2116_goal_bucket_distribution_after_filter_has_hit():
    matches = add_strength_snapshots(_prepare_matches(_fixtures(), "Premier League", "2025/26"), min_strength_matches=1)
    row = analyze_match_strategy(matches, 5, "BASELINE_UNFILTERED")
    assert row["final_reference_count"] > 0
    assert row["final_reference_top_goal_bucket"] in {"GOALS_0_1", "GOALS_2_3", "GOALS_4_PLUS", "NO_CLEAR_TOP"}
