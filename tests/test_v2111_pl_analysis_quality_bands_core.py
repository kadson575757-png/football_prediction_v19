import pandas as pd

from scripts.evaluate_v2111_pl_2025_26_analysis_quality import compute_quality_band_breakdown


def test_v2111_quality_band_breakdown_hit_rates():
    rows = pd.DataFrame([
        {"probability_edge_band": "LOW", "uncertainty_level": "HIGH", "data_quality_band": "PARTIAL", "source_quality_band": "LOW", "top_probability_hit": True},
        {"probability_edge_band": "LOW", "uncertainty_level": "HIGH", "data_quality_band": "PARTIAL", "source_quality_band": "LOW", "top_probability_hit": False},
        {"probability_edge_band": "HIGH", "uncertainty_level": "LOW", "data_quality_band": "FULL", "source_quality_band": "FULL", "top_probability_hit": True},
    ])

    breakdown = compute_quality_band_breakdown(rows)
    edge_low = breakdown[(breakdown["breakdown_type"] == "probability_edge_band") & (breakdown["band"] == "LOW")].iloc[0]

    assert edge_low["n"] == 2
    assert edge_low["hit_count"] == 1
    assert edge_low["hit_rate"] == 0.5

