import pandas as pd

from scripts.analyze_v298_promising_indicator_mix import (
    apply_promising_indicator_mix,
    combined_shadow_predicted_winner,
    prepare_promising_mix_frame,
)


def test_v298_deltas_are_calculated_from_base_gd_gf_ga():
    frame = pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.40,
                "base_draw_probability": 0.30,
                "base_away_probability": 0.30,
                "gd_adjusted_home_win_probability": 0.43,
                "gd_adjusted_away_probability": 0.27,
                "gf_adjusted_home_win_probability": 0.42,
                "gf_adjusted_away_probability": 0.28,
                "ga_adjusted_home_win_probability": 0.38,
                "ga_adjusted_away_probability": 0.32,
            }
        ]
    )

    work = prepare_promising_mix_frame(frame)

    assert round(float(work.loc[0, "gd_home_delta"]), 4) == 0.03
    assert round(float(work.loc[0, "gd_away_delta"]), 4) == -0.03
    assert round(float(work.loc[0, "gf_home_delta"]), 4) == 0.02
    assert round(float(work.loc[0, "gf_away_delta"]), 4) == -0.02
    assert round(float(work.loc[0, "ga_home_delta"]), 4) == -0.02
    assert round(float(work.loc[0, "ga_away_delta"]), 4) == 0.02


def test_v298_combined_probabilities_sum_to_one_and_shift_cap_applies():
    frame = pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.40,
                "base_draw_probability": 0.30,
                "base_away_probability": 0.30,
                "gd_adjusted_home_win_probability": 0.50,
                "gd_adjusted_away_probability": 0.20,
                "gf_adjusted_home_win_probability": 0.50,
                "gf_adjusted_away_probability": 0.20,
                "ga_adjusted_home_win_probability": 0.50,
                "ga_adjusted_away_probability": 0.20,
                "real_result": "HOME_WIN",
            }
        ]
    )
    work = prepare_promising_mix_frame(frame)

    mixed = apply_promising_indicator_mix(work, gd_weight=1.0, gf_weight=1.0, ga_weight=1.0)

    total = mixed.loc[0, "combined_shadow_home_probability"] + mixed.loc[0, "combined_shadow_draw_probability"] + mixed.loc[0, "combined_shadow_away_probability"]
    assert abs(total - 1.0) < 0.0001
    assert mixed.loc[0, "combined_shadow_home_probability"] <= 0.48


def test_v298_no_clear_winner_when_home_away_difference_small():
    assert combined_shadow_predicted_winner(0.41, 0.38) == "NO_CLEAR_WINNER"
    assert combined_shadow_predicted_winner(0.42, 0.38) == "HOME"
    assert combined_shadow_predicted_winner(0.38, 0.42) == "AWAY"
