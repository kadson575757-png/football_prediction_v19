import pandas as pd

from football_prediction_v19.analysis.v2117_draw_bias_diagnostics import compute_threshold_probe


def test_v2117_threshold_probe_precision_recall_and_zero_division():
    rows = pd.DataFrame([
        {"actual_result": "DRAW", "draw_probability": 0.31},
        {"actual_result": "HOME", "draw_probability": 0.33},
        {"actual_result": "DRAW", "draw_probability": 0.20},
    ])
    out = compute_threshold_probe(rows, thresholds=[0.30, 0.40])
    first = out[out["threshold"].eq(0.30)].iloc[0]
    assert first["candidate_count"] == 2
    assert first["actual_draw_count"] == 1
    assert first["false_draw_count"] == 1
    assert first["precision"] == 0.5
    assert first["recall"] == 0.5
    second = out[out["threshold"].eq(0.40)].iloc[0]
    assert second["candidate_count"] == 0
    assert second["precision"] == 0.0
