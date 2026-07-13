import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import apply_edge_calibration_integration, prepare_integration_rows


def test_no_adjustment_at_or_below_threshold():
    rows = prepare_integration_rows(pd.DataFrame([{"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.5, "draw_probability": 0.3, "away_probability": 0.2, "probability_edge": edge} for edge in [0.10, 0.15]]))
    result, _ = apply_edge_calibration_integration(rows)
    assert not result["edge_calibration_applied"].any()
    assert result["calibrated_home_win_probability"].tolist() == [0.5, 0.5]
