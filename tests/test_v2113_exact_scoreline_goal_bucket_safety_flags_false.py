import pandas as pd

from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import analyze_exact_scoreline_goal_buckets


def test_v2113_exact_scoreline_goal_bucket_safety_flags_false(tmp_path):
    fixtures = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "Arsenal", "away_team": "Chelsea", "actual_home_goals": 2, "actual_away_goals": 1},
        {"match_date": "2025-08-08", "home_team": "Liverpool", "away_team": "Everton", "actual_home_goals": 1, "actual_away_goals": 1},
    ])

    result = analyze_exact_scoreline_goal_buckets(fixtures, output_dir=tmp_path)

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    rows = pd.read_csv(result["rows_csv_path"], keep_default_na=False)
    assert str(rows.loc[0, "automatic_betting_enabled"]).lower() == "false"
    assert str(rows.loc[0, "staking_logic_enabled"]).lower() == "false"
    assert str(rows.loc[0, "roi_logic_enabled"]).lower() == "false"
