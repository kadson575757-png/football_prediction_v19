import pandas as pd

from scripts.generate_v299_winner_explanation_report import generate_winner_explanation_report


def test_v299_safety_flags_false(tmp_path):
    rows = tmp_path / "rows.csv"
    pd.DataFrame(
        [
            {
                "competition": "Premier League",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "base_home_win_probability": 0.42,
                "base_draw_probability": 0.29,
                "base_away_probability": 0.29,
                "home_win_probability": 0.42,
                "draw_probability": 0.29,
                "away_win_probability": 0.29,
                "gd_adjusted_home_win_probability": 0.45,
                "gd_adjusted_away_probability": 0.26,
                "gf_adjusted_home_win_probability": 0.44,
                "gf_adjusted_away_probability": 0.27,
                "ga_adjusted_home_win_probability": 0.43,
                "ga_adjusted_away_probability": 0.28,
                "decision_class": "WINNER_LEAN",
                "real_result": "HOME_WIN",
                "evaluation_result": "HIT",
            }
        ]
    ).to_csv(rows, index=False)

    result = generate_winner_explanation_report(rows, tmp_path / "out")

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
