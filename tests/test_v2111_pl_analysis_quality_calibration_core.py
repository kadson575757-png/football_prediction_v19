import pandas as pd

from scripts.evaluate_v2111_pl_2025_26_analysis_quality import compute_calibration_buckets, compute_quality_summary


def test_v2111_calibration_buckets_and_summary():
    rows = pd.DataFrame([
        {"top_probability_outcome": "HOME", "home_win_probability": 0.36, "draw_probability": 0.32, "away_win_probability": 0.32, "actual_result": "HOME", "top_probability_hit": True},
        {"top_probability_outcome": "HOME", "home_win_probability": 0.38, "draw_probability": 0.31, "away_win_probability": 0.31, "actual_result": "AWAY", "top_probability_hit": False},
        {"top_probability_outcome": "AWAY", "home_win_probability": 0.2, "draw_probability": 0.2, "away_win_probability": 0.61, "actual_result": "AWAY", "top_probability_hit": True},
    ])

    buckets = compute_calibration_buckets(rows)
    summary = compute_quality_summary(rows)

    bucket = buckets[buckets["bucket"] == "0.35-0.40"].iloc[0]
    assert bucket["n"] == 2
    assert bucket["hit_rate"] == 0.5
    assert summary["average_top_probability"] == 0.45
    assert summary["empirical_top_hit_rate"] == 0.6667
    assert "expected_calibration_error" in summary
    assert "max_calibration_error" in summary

