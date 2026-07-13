import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import apply_edge_calibration_integration, prepare_integration_rows


def test_unchanged_rows_have_exact_calibrated_parity():
    rows = prepare_integration_rows(pd.DataFrame([{"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.40, "draw_probability": 0.35, "away_probability": 0.25, "probability_edge": 0.05}]))
    result, audit = apply_edge_calibration_integration(rows)
    row = result.iloc[0]
    assert (row["calibrated_home_win_probability"], row["calibrated_draw_probability"], row["calibrated_away_win_probability"]) == (0.40, 0.35, 0.25)
    assert not audit.iloc[0]["unchanged_row_mismatch"]
