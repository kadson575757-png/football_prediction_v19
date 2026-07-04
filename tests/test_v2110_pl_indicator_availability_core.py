import pandas as pd

from scripts.run_v2110_premier_league_2025_26_full_season_analysis import compute_indicator_availability


def test_v2110_indicator_availability_counts_quality_and_applied_rates():
    rows = pd.DataFrame([
        {"dt_indicator_quality": "FULL", "dt_adjustment_applied": True},
        {"dt_indicator_quality": "PARTIAL", "dt_adjustment_applied": False},
        {"dt_indicator_quality": "LOW", "dt_adjustment_applied": "true"},
        {"dt_indicator_quality": "", "dt_adjustment_applied": ""},
    ])

    result = compute_indicator_availability(rows)
    dt = result[result["prefix"] == "dt"].iloc[0]

    assert dt["full_quality_count"] == 1
    assert dt["partial_quality_count"] == 1
    assert dt["low_quality_count"] == 1
    assert dt["missing_count"] == 1
    assert dt["adjustment_applied_count"] == 2
    assert dt["full_quality_rate"] == 0.25
    assert dt["adjustment_applied_rate"] == 0.5

