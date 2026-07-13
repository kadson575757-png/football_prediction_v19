import pandas as pd

from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import assign_time_segments


def test_time_segmentation_produces_four_chronological_near_equal_periods():
    rows = pd.DataFrame([{"match_date": f"2025-01-{day:02d}"} for day in range(1, 11)])
    segmented = assign_time_segments(rows)
    assert segmented["period"].drop_duplicates().tolist() == ["PERIOD_1", "PERIOD_2", "PERIOD_3", "PERIOD_4"]
    counts = segmented.groupby("period").size()
    assert counts.max() - counts.min() <= 1
