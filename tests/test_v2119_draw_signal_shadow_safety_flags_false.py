import pandas as pd

from football_prediction_v19.analysis.v2119_draw_signal_shadow_probe import analyze_draw_signal_shadow_probe


def test_v2119_draw_signal_shadow_safety_flags_false(tmp_path):
    rows = pd.DataFrame([
        {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.34, "draw_probability": 0.31, "away_win_probability": 0.36, "probability_edge": 0.05},
        {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.50, "draw_probability": 0.27, "away_win_probability": 0.23, "probability_edge": 0.05},
    ])
    result = analyze_draw_signal_shadow_probe(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert (tmp_path / "v2119_draw_signal_shadow_summary.json").exists()
