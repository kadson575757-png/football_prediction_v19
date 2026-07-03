from football_prediction_v19.analysis.v2109_shadow_consensus_alignment_indicator import build_shadow_consensus_alignment_indicator


def test_shadow_consensus_alignment_counts_support_and_ignores_low_quality():
    source = {
        "dt_indicator_quality": "FULL", "dt_adjustment_applied": True, "dt_adjusted_home_win_probability": 0.5, "dt_adjusted_draw_probability": 0.3, "dt_adjusted_away_probability": 0.2,
        "vr_indicator_quality": "FULL", "vr_adjustment_applied": True, "vr_adjusted_home_win_probability": 0.49, "vr_adjusted_draw_probability": 0.31, "vr_adjusted_away_probability": 0.2,
        "gm_indicator_quality": "PARTIAL", "gm_adjustment_applied": False, "gm_adjusted_home_win_probability": 0.3, "gm_adjusted_draw_probability": 0.45, "gm_adjusted_away_probability": 0.25,
        "vsb_indicator_quality": "LOW", "vsb_adjustment_applied": True, "vsb_adjusted_home_win_probability": 0.1, "vsb_adjusted_draw_probability": 0.1, "vsb_adjusted_away_probability": 0.8,
    }

    result = build_shadow_consensus_alignment_indicator(0.42, 0.31, 0.27, source)

    assert result["sca_available_shadow_count"] == 3
    assert result["sca_home_support_count"] == 2.0
    assert result["sca_draw_support_count"] == 0.5
    assert result["sca_away_support_count"] == 0.0
    assert result["sca_consensus_top_outcome"] == "HOME"
    assert result["sca_conflict_count"] == 0.5
    assert round(result["sca_adjusted_home_win_probability"] + result["sca_adjusted_draw_probability"] + result["sca_adjusted_away_probability"], 6) == 1.0
