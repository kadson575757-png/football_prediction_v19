import pandas as pd

from scripts.analyze_v2103_probability_calibration import (
    build_bucket_summary,
    build_calibration_rows,
    build_calibration_summary,
    calibration_bucket,
)


def test_v2103_probability_calibration_buckets_and_errors():
    source = pd.DataFrame(
        [
            _row(0.34, 0.33, 0.33, "HOME", "HOME"),
            _row(0.36, 0.32, 0.32, "HOME", "AWAY"),
            _row(0.42, 0.30, 0.28, "HOME", "HOME"),
            _row(0.46, 0.29, 0.25, "HOME", "DRAW"),
            _row(0.46, 0.28, 0.26, "HOME", "AWAY"),
            _row(0.46, 0.27, 0.27, "HOME", "DRAW"),
            _row(0.46, 0.27, 0.27, "HOME", "AWAY"),
        ]
    )

    rows = build_calibration_rows(source)
    buckets = build_bucket_summary(rows)
    summary = build_calibration_summary(rows, rows, buckets)

    assert calibration_bucket(0.34) == "0.30-0.35"
    assert calibration_bucket(0.35) == "0.35-0.40"
    assert calibration_bucket(0.70) == "0.70-1.00"
    assert buckets.loc[buckets["bucket_name"].eq("0.45-0.50"), "rows_count"].iloc[0] == 4
    assert summary["expected_calibration_error"] == 0.4914
    assert summary["max_calibration_error"] == 0.66
    assert summary["worst_calibration_bucket"] == "0.45-0.50"


def _row(home, draw, away, top, real):
    return {
        "competition": "Premier League",
        "season": "2025/26",
        "home_team": "A",
        "away_team": "B",
        "match_date": "2026-03-01",
        "home_win_probability": home,
        "draw_probability": draw,
        "away_win_probability": away,
        "top_probability_outcome": top,
        "real_result": real,
    }
