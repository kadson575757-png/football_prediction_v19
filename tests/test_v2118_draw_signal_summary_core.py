import pandas as pd

from football_prediction_v19.analysis.v2118_draw_signal_discovery import analyze_draw_signal_discovery


def test_v2118_draw_signal_summary_core(tmp_path):
    rows = pd.DataFrame(
        [{"actual_result": "DRAW", "home_win_probability": 0.34, "draw_probability": 0.30, "away_win_probability": 0.33, "probability_edge": 0.02}]
        + [{"actual_result": "HOME", "home_win_probability": 0.50, "draw_probability": 0.25, "away_win_probability": 0.25, "probability_edge": 0.25} for _ in range(3)]
    )
    result = analyze_draw_signal_discovery(rows, output_dir=tmp_path, min_sample=1)
    assert result["v2118_draw_signal_discovery_status"] == "READY"
    assert result["rows_loaded"] == 4
    assert result["actual_draw_count"] == 1
    assert result["baseline_draw_rate"] == 0.25
    assert result["best_signal_name"] != ""
