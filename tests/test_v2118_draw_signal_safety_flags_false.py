import pandas as pd

from football_prediction_v19.analysis.v2118_draw_signal_discovery import analyze_draw_signal_discovery


def test_v2118_draw_signal_safety_flags_false(tmp_path):
    rows = pd.DataFrame([
        {"actual_result": "DRAW", "home_win_probability": 0.34, "draw_probability": 0.30, "away_win_probability": 0.33, "probability_edge": 0.02},
        {"actual_result": "HOME", "home_win_probability": 0.50, "draw_probability": 0.25, "away_win_probability": 0.25, "probability_edge": 0.25},
    ])
    result = analyze_draw_signal_discovery(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert (tmp_path / "v2118_draw_signal_summary.json").exists()
