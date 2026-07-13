import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import analyze_edge_calibration_integration


def test_brier_improvement_reproduces_for_correct_high_edge_rows(tmp_path):
    row = {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}
    result = analyze_edge_calibration_integration(pd.DataFrame([row]), pd.DataFrame([row]), output_dir=tmp_path)
    assert result["brier_improvement"] > 0
    assert result["premier_league_brier_improvement"] > 0
    assert result["external_league_brier_improvement"] > 0
