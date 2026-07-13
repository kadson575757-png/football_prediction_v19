import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import BASE_COLUMNS, apply_edge_calibration_integration, prepare_integration_rows


def test_base_fields_remain_exactly_unchanged():
    rows = prepare_integration_rows(pd.DataFrame([{"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}]))
    before = rows[BASE_COLUMNS].copy(deep=True)
    result, audit = apply_edge_calibration_integration(rows)
    pd.testing.assert_frame_equal(result[BASE_COLUMNS], before)
    assert not audit["base_probability_parity_mismatch"].any()
