import pandas as pd

from football_prediction_v19.analysis.v2119_draw_signal_shadow_probe import apply_shadow_strategy, compute_strategy_metrics, prepare_shadow_rows


def test_v2119_shadow_metrics_core():
    rows = prepare_shadow_rows(pd.DataFrame([
        {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.34, "draw_probability": 0.31, "away_win_probability": 0.36, "probability_edge": 0.05},
        {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.50, "draw_probability": 0.27, "away_win_probability": 0.23, "probability_edge": 0.05},
        {"actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.20, "draw_probability": 0.25, "away_win_probability": 0.55, "probability_edge": 0.35},
    ]))
    baseline_rate = 2 / 3
    strategy_rows = apply_shadow_strategy(rows, "EDGE_3_6_DRAW_TOP")
    metrics = compute_strategy_metrics("EDGE_3_6_DRAW_TOP", strategy_rows, baseline_rate=round(baseline_rate, 4))
    assert metrics["hit_count"] == 2
    assert metrics["hit_rate"] == round(2 / 3, 4)
    assert metrics["delta_vs_baseline"] == 0.0
    assert metrics["draw_prediction_count"] == 2
    assert metrics["draw_hit_count"] == 1
    assert metrics["draw_false_count"] == 1
    assert metrics["draw_precision"] == 0.5
    assert metrics["draw_recall"] == 1.0
    assert metrics["newly_captured_draw_count"] == 1
    assert metrics["newly_created_false_draw_count"] == 1
