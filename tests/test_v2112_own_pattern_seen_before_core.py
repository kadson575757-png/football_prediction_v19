import pandas as pd

from scripts.analyze_v2112_exact_scoreline_pattern_test import analyze_exact_scoreline_patterns


def test_v2112_own_pattern_seen_before_excludes_last_match_itself(tmp_path):
    fixtures = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "Arsenal", "away_team": "Team A", "actual_home_goals": 3, "actual_away_goals": 1},
        {"match_date": "2025-08-08", "home_team": "Arsenal", "away_team": "Team B", "actual_home_goals": 3, "actual_away_goals": 1},
        {"match_date": "2025-08-15", "home_team": "Arsenal", "away_team": "Team C", "actual_home_goals": 2, "actual_away_goals": 0},
    ])

    result = analyze_exact_scoreline_patterns(fixtures, output_dir=tmp_path)
    rows = pd.read_csv(result["rows_csv_path"], keep_default_na=False)
    target = rows[rows["match_date"] == "2025-08-15"].iloc[0]

    assert target["home_last_pattern"] == "W 3:1"
    assert bool(target["home_own_pattern_seen_before"]) is True
    assert target["home_own_pattern_seen_before_count"] == 1

