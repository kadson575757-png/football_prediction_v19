import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import apply_edge_calibration_integration, prepare_integration_rows


def test_high_edge_sharpen_005_exact():
    rows = prepare_integration_rows(pd.DataFrame([{"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}]))
    result, audit = apply_edge_calibration_integration(rows)
    row = result.iloc[0]
    assert row["calibrated_home_win_probability"] == 0.555
    assert row["edge_calibration_method"] == "HIGH_EDGE_SHARPEN_005"
    assert row["edge_calibration_applied"]
    assert not audit.iloc[0]["calibration_formula_mismatch"]
