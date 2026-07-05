import pandas as pd
from pathlib import Path

from scripts.evaluate_v2111_pl_2025_26_analysis_quality import evaluate_pl_analysis_quality


def test_v2111_analysis_quality_safety_flags_false_and_outputs_written(tmp_path):
    analysis = pd.DataFrame([{
        "competition": "Premier League",
        "season": "2025/26",
        "match_date": "2025-08-16",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "top_probability_outcome": "HOME",
        "home_win_probability": 0.42,
        "draw_probability": 0.30,
        "away_win_probability": 0.28,
    }])
    results = pd.DataFrame([{
        "competition": "Premier League",
        "season": "2025/26",
        "match_date": "2025-08-16",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "actual_home_goals": 2,
        "actual_away_goals": 1,
    }])

    result = evaluate_pl_analysis_quality(analysis, results_frame=results, output_dir=tmp_path)

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert Path(result["quality_rows_csv_path"]).exists()
    assert Path(result["quality_summary_json_path"]).exists()
    assert Path(result["quality_report_md_path"]).exists()
    assert Path(result["confusion_matrix_csv_path"]).exists()
    assert Path(result["calibration_buckets_csv_path"]).exists()
    assert Path(result["quality_band_breakdown_csv_path"]).exists()
    assert Path(result["indicator_quality_vs_hit_rate_csv_path"]).exists()
