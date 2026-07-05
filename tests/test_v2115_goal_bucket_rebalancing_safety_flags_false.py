import pandas as pd
from pathlib import Path

from scripts.analyze_v2115_goal_bucket_rebalancing_test import analyze_goal_bucket_rebalancing


def test_v2115_goal_bucket_rebalancing_safety_flags_false_and_outputs(tmp_path):
    rows = pd.DataFrame([{
        "actual_goal_bucket": "GOALS_2_3",
        "final_reference_top_goal_bucket": "GOALS_2_3",
        "final_goal_reference_count": 7,
        "final_reference_goals_0_1_rate": 0.1,
        "final_reference_goals_2_3_rate": 0.6,
        "final_reference_goals_4_plus_rate": 0.3,
        "combined_single_top_goal_bucket": "GOALS_2_3",
        "combined_single_goal_reference_count": 7,
        "away_single_top_goal_bucket": "GOALS_4_PLUS",
    }])

    result = analyze_goal_bucket_rebalancing(rows, tmp_path)

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert Path(result["strategy_summary_csv_path"]).exists()
    assert Path(result["rows_csv_path"]).exists()
    assert Path(result["summary_json_path"]).exists()
    assert Path(result["report_md_path"]).exists()
