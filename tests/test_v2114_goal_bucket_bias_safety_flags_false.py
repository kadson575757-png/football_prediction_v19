import pandas as pd

from scripts.analyze_v2114_goal_bucket_bias_diagnostics import analyze_goal_bucket_bias


def test_v2114_goal_bucket_bias_safety_flags_false(tmp_path):
    rows = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "A", "away_team": "B", "actual_total_goals": 3, "actual_goal_bucket": "GOALS_2_3", "final_goal_reference_source": "COMBINED_SINGLE", "final_goal_reference_count": 1, "final_reference_top_goal_bucket": "GOALS_2_3", "goal_bucket_hit": True},
    ])
    result = analyze_goal_bucket_bias(rows, output_dir=tmp_path)

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
