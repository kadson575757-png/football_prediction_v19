from football_prediction_v19.analysis.v2105_combined_indicator_shadow_mix import build_combined_indicator_shadow_mix


def _ind(name, quality="FULL", home=0.45, draw=0.3, away=0.25, applied=True):
    return {"indicator_name": name, "indicator_quality": quality, "adjustment_applied": applied, "adjusted_home_win_probability": home, "adjusted_draw_probability": draw, "adjusted_away_probability": away}


def test_v2105_combined_mix_v2104_and_v2105_missing_and_low_safe():
    result = build_combined_indicator_shadow_mix(
        0.4,
        0.3,
        0.3,
        [_ind("DRAW_TENDENCY", draw=0.36, home=0.37, away=0.27), _ind("CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", home=0.45), _ind("COMEBACK_BLOWN_LEAD_PROFILE", "LOW", home=0.9), {}],
        max_total_shift=0.04,
    )

    assert result["combined_mix_indicator_count"] == 2
    assert "DRAW_TENDENCY" in result["combined_mix_included_indicators"]
    assert "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE" in result["combined_mix_included_indicators"]
    assert result["combined_mix_total_shift"] <= 0.04
    assert round(result["combined_mix_adjusted_home_win_probability"] + result["combined_mix_adjusted_draw_probability"] + result["combined_mix_adjusted_away_probability"], 4) == 1.0
