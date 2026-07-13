import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import apply_edge_calibration_integration, prepare_integration_rows


def test_calibrated_probability_sum_is_exactly_one():
    rows = prepare_integration_rows(pd.DataFrame([{"actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.20, "draw_probability": 0.25, "away_probability": 0.55, "probability_edge": 0.30}]))
    result, _ = apply_edge_calibration_integration(rows)
    row = result.iloc[0]
    assert row["calibrated_probability_sum"] == 1.0
    assert row["probability_sum_error"] == 0.0
