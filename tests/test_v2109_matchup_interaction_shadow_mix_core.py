from football_prediction_v19.analysis.v2109_matchup_interaction_shadow_mix import build_v2109_matchup_interaction_shadow_mix


def _ind(name, quality="FULL", home=0.45, draw=0.3, away=0.25, applied=True):
    return {"indicator_name": name, "indicator_quality": quality, "adjustment_applied": applied, "adjusted_home_win_probability": home, "adjusted_draw_probability": draw, "adjusted_away_probability": away}


def test_v2109_matchup_mix_one_and_multiple_low_ignored():
    one = build_v2109_matchup_interaction_shadow_mix(0.4, 0.3, 0.3, [_ind("ATTACK_DEFENSE_MATCHUP_PROFILE")])
    many = build_v2109_matchup_interaction_shadow_mix(0.4, 0.3, 0.3, [_ind("ATTACK_DEFENSE_MATCHUP_PROFILE"), _ind("VENUE_SPLIT_DELTA_PROFILE", home=0.44), _ind("DRAW_PRESSURE_COMPOSITE_PROFILE", "LOW", home=0.9)])

    assert one["v2109_mix_indicator_count"] == 1
    assert many["v2109_mix_indicator_count"] == 2
    assert "DRAW_PRESSURE_COMPOSITE_PROFILE" not in many["v2109_mix_included_indicators"]
    assert round(many["v2109_mix_adjusted_home_win_probability"] + many["v2109_mix_adjusted_draw_probability"] + many["v2109_mix_adjusted_away_probability"], 6) == 1.0


def test_v2109_matchup_mix_weights_and_max_shift():
    result = build_v2109_matchup_interaction_shadow_mix(0.4, 0.3, 0.3, [_ind("ATTACK_DEFENSE_MATCHUP_PROFILE", home=0.8, draw=0.1, away=0.1), _ind("DRAW_PRESSURE_COMPOSITE_PROFILE", home=0.2, draw=0.7, away=0.1)], weights={"DRAW_PRESSURE_COMPOSITE_PROFILE": 1.0}, max_total_shift=0.03)

    assert result["v2109_mix_indicator_count"] == 1
    assert result["v2109_mix_total_shift"] <= 0.03
    assert result["v2109_mix_adjusted_draw_probability"] > 0.3
