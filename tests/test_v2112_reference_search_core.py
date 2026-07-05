import pandas as pd

from scripts.analyze_v2112_exact_scoreline_pattern_test import _prepare_matches, find_references


def test_v2112_reference_search_exact_home_away_and_combined_unique():
    fixtures = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "A", "away_team": "X", "actual_home_goals": 1, "actual_away_goals": 0},
        {"match_date": "2025-08-01", "home_team": "B", "away_team": "Y", "actual_home_goals": 1, "actual_away_goals": 0},
        {"match_date": "2025-08-08", "home_team": "A", "away_team": "B", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-15", "home_team": "C", "away_team": "Z", "actual_home_goals": 1, "actual_away_goals": 0},
        {"match_date": "2025-08-15", "home_team": "D", "away_team": "W", "actual_home_goals": 0, "actual_away_goals": 1},
        {"match_date": "2025-08-22", "home_team": "C", "away_team": "D", "actual_home_goals": 1, "actual_away_goals": 1},
    ])
    matches = _prepare_matches(fixtures, "Premier League", "2025/26")
    refs = find_references(matches, 5, "W 1:0", "W 1:0")

    assert refs["exact_pair"]["reference_count"] == 1
    assert refs["home_single"]["reference_count"] == 1
    assert refs["away_single"]["reference_count"] == 1
    assert refs["combined_single"]["reference_count"] == 1
