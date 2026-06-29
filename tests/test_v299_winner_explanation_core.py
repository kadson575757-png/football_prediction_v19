import pandas as pd

from scripts.generate_v299_winner_explanation_report import (
    build_explanation_frame,
    direction_from_edge,
)


def test_v299_base_direction_support_conflict_and_consensus():
    frame = pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.45,
                "base_draw_probability": 0.25,
                "base_away_probability": 0.30,
                "home_win_probability": 0.45,
                "draw_probability": 0.25,
                "away_win_probability": 0.30,
                "gd_adjusted_home_win_probability": 0.47,
                "gd_adjusted_away_probability": 0.28,
                "gf_adjusted_home_win_probability": 0.46,
                "gf_adjusted_away_probability": 0.29,
                "ga_adjusted_home_win_probability": 0.41,
                "ga_adjusted_away_probability": 0.34,
                "decision_class": "WINNER_LEAN",
                "evaluation_result": "HIT",
            }
        ]
    )

    work = build_explanation_frame(frame)

    assert direction_from_edge(0.05) == "HOME"
    assert work.loc[0, "base_direction"] == "HOME"
    assert work.loc[0, "promising_indicator_support_count"] == 3
    assert work.loc[0, "promising_indicator_conflict_count"] == 0
    assert work.loc[0, "promising_indicator_consensus"] == "HOME"
    assert work.loc[0, "explanation_label"] == "BASE_AND_SHADOWS_ALIGN"


def test_v299_conflict_label_for_strong_base_conflict():
    frame = pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.50,
                "base_draw_probability": 0.25,
                "base_away_probability": 0.25,
                "gd_adjusted_home_win_probability": 0.28,
                "gd_adjusted_away_probability": 0.47,
                "gf_adjusted_home_win_probability": 0.29,
                "gf_adjusted_away_probability": 0.46,
                "ga_adjusted_home_win_probability": 0.51,
                "ga_adjusted_away_probability": 0.24,
                "decision_class": "WINNER_LEAN",
            }
        ]
    )

    work = build_explanation_frame(frame)

    assert work.loc[0, "base_direction"] == "HOME"
    assert work.loc[0, "promising_indicator_conflict_count"] == 2
    assert work.loc[0, "promising_indicator_consensus"] == "AWAY"
    assert work.loc[0, "explanation_label"] == "BASE_STRONG_SHADOW_CONFLICT"


def test_v299_no_decision_shadow_home_and_no_signal_labels():
    frame = pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.39,
                "base_draw_probability": 0.25,
                "base_away_probability": 0.37,
                "gd_adjusted_home_win_probability": 0.45,
                "gd_adjusted_away_probability": 0.30,
                "gf_adjusted_home_win_probability": 0.44,
                "gf_adjusted_away_probability": 0.31,
                "ga_adjusted_home_win_probability": 0.40,
                "ga_adjusted_away_probability": 0.38,
                "decision_class": "NO_DECISION",
            },
            {
                "base_home_win_probability": 0.39,
                "base_draw_probability": 0.25,
                "base_away_probability": 0.37,
                "gd_adjusted_home_win_probability": 0.40,
                "gd_adjusted_away_probability": 0.38,
                "gf_adjusted_home_win_probability": 0.39,
                "gf_adjusted_away_probability": 0.37,
                "ga_adjusted_home_win_probability": 0.39,
                "ga_adjusted_away_probability": 0.38,
                "decision_class": "NO_DECISION",
            },
        ]
    )

    work = build_explanation_frame(frame)

    assert work.loc[0, "explanation_label"] == "NO_DECISION_SHADOW_HOME"
    assert work.loc[1, "explanation_label"] == "NO_DECISION_NO_SIGNAL"
