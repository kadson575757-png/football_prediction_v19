import pandas as pd

from scripts.evaluate_v2111_pl_2025_26_analysis_quality import compute_indicator_quality_vs_hit_rate


def test_v2111_indicator_quality_vs_hit_rate_counts():
    rows = pd.DataFrame([
        {"dt_indicator_quality": "FULL", "dt_adjustment_applied": True, "top_probability_hit": True},
        {"dt_indicator_quality": "FULL", "dt_adjustment_applied": False, "top_probability_hit": False},
        {"dt_indicator_quality": "LOW", "dt_adjustment_applied": False, "top_probability_hit": True},
    ])

    result = compute_indicator_quality_vs_hit_rate(rows)
    dt = result[result["prefix"] == "dt"].iloc[0]

    assert dt["full_quality_count"] == 2
    assert dt["low_quality_count"] == 1
    assert dt["adjustment_applied_count"] == 1
    assert dt["hit_rate_when_full"] == 0.5
    assert dt["hit_rate_when_low"] == 1.0
    assert dt["hit_rate_when_adjustment_applied"] == 1.0
    assert dt["hit_rate_when_no_adjustment"] == 0.5

