import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import apply_edge_calibration_integration, prepare_integration_rows


def test_deduction_is_proportional_across_non_top_outcomes():
    rows = prepare_integration_rows(pd.DataFrame([{"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.60, "draw_probability": 0.30, "away_probability": 0.10, "probability_edge": 0.30}]))
    result, _ = apply_edge_calibration_integration(rows)
    row = result.iloc[0]
    draw_reduction = 0.30 - row["calibrated_draw_probability"]
    away_reduction = 0.10 - row["calibrated_away_win_probability"]
    assert round(draw_reduction / away_reduction, 8) == 3.0
    assert round(draw_reduction + away_reduction, 8) == 0.005
