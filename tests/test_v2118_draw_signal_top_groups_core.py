import pandas as pd

from football_prediction_v19.analysis.v2118_draw_signal_discovery import top_signal_groups


def test_v2118_top_groups_prefers_min_sample_then_draw_rate():
    groups = pd.DataFrame([
        {"signal_name": "a", "signal_group": "tiny", "count": 2, "draw_count": 2, "draw_rate": 1.0, "lift_vs_baseline": 0.5, "low_sample": True},
        {"signal_name": "b", "signal_group": "stable", "count": 20, "draw_count": 10, "draw_rate": 0.5, "lift_vs_baseline": 0.1, "low_sample": False},
    ])
    ranked = top_signal_groups(groups, min_sample=20)
    assert ranked.iloc[0]["signal_group"] == "stable"
