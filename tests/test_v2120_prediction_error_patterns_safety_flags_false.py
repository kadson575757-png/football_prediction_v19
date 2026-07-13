import json

import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import analyze_prediction_error_patterns


def test_v2120_safety_flags_are_false_and_outputs_exist(tmp_path):
    rows = pd.DataFrame([
        {"home_team": "A", "away_team": "B", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.46, "draw_probability": 0.29, "away_probability": 0.25, "probability_edge": 0.17},
        {"home_team": "C", "away_team": "D", "actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.31, "draw_probability": 0.31, "away_probability": 0.38, "probability_edge": 0.07},
    ])
    result = analyze_prediction_error_patterns(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert result["hit_count"] == 1
    assert result["miss_count"] == 1
    assert result["home_top_count"] == 1
    assert result["away_top_count"] == 1
    assert result["actual_draw_count"] == 1
    payload = json.loads((tmp_path / "v2120_prediction_error_patterns_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    assert payload["staking_logic_enabled"] is False
    assert payload["roi_logic_enabled"] is False
    assert (tmp_path / "v2120_wrong_high_confidence_rows.csv").exists()
    assert (tmp_path / "v2120_prediction_error_patterns_report.md").exists()
