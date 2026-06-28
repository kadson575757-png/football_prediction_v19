import pandas as pd

from scripts.analyze_v293_combined_shadow_mix import (
    apply_combined_shadow_mix,
    combined_shadow_predicted_winner,
    prepare_shadow_mix_frame,
)


def test_v293_deltas_are_calculated_from_base_ppg_last5():
    frame = pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.40,
                "base_draw_probability": 0.30,
                "base_away_probability": 0.30,
                "ppg_adjusted_home_win_probability": 0.43,
                "ppg_adjusted_away_probability": 0.27,
                "last5_adjusted_home_win_probability": 0.38,
                "last5_adjusted_away_probability": 0.32,
            }
        ]
    )

    work = prepare_shadow_mix_frame(frame)

    assert round(float(work.loc[0, "ppg_home_delta"]), 4) == 0.03
    assert round(float(work.loc[0, "ppg_away_delta"]), 4) == -0.03
    assert round(float(work.loc[0, "last5_home_delta"]), 4) == -0.02
    assert round(float(work.loc[0, "last5_away_delta"]), 4) == 0.02


def test_v293_combined_probabilities_sum_to_one_and_shift_cap_applies():
    frame = pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.40,
                "base_draw_probability": 0.30,
                "base_away_probability": 0.30,
                "ppg_adjusted_home_win_probability": 0.50,
                "ppg_adjusted_away_probability": 0.20,
                "last5_adjusted_home_win_probability": 0.50,
                "last5_adjusted_away_probability": 0.20,
                "real_result": "HOME_WIN",
            }
        ]
    )
    work = prepare_shadow_mix_frame(frame)

    mixed = apply_combined_shadow_mix(work, ppg_weight=1.0, last5_weight=1.0)

    total = mixed.loc[0, "combined_shadow_home_probability"] + mixed.loc[0, "combined_shadow_draw_probability"] + mixed.loc[0, "combined_shadow_away_probability"]
    assert abs(total - 1.0) < 0.0001
    assert mixed.loc[0, "combined_shadow_home_probability"] <= 0.46


def test_v293_no_clear_winner_when_home_away_difference_small():
    assert combined_shadow_predicted_winner(0.41, 0.38) == "NO_CLEAR_WINNER"
    assert combined_shadow_predicted_winner(0.45, 0.38) == "HOME"
    assert combined_shadow_predicted_winner(0.38, 0.45) == "AWAY"
