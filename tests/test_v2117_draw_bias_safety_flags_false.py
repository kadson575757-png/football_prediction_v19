import pandas as pd

from football_prediction_v19.analysis.v2117_draw_bias_diagnostics import analyze_draw_bias


def test_v2117_draw_bias_safety_flags_false_and_outputs(tmp_path):
    rows = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "A", "away_team": "B", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.34, "draw_probability": 0.31, "away_win_probability": 0.35},
        {"match_date": "2025-08-02", "home_team": "C", "away_team": "D", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.50, "draw_probability": 0.25, "away_win_probability": 0.25},
    ])
    result = analyze_draw_bias(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert (tmp_path / "v2117_missed_draw_rows.csv").exists()
    assert (tmp_path / "v2117_draw_bias_report.md").exists()
