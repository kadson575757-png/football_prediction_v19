import pandas as pd

from scripts.analyze_v298_promising_indicator_mix import analyze_promising_indicator_mix


def test_v298_safety_flags_false(tmp_path):
    rows = tmp_path / "rows.csv"
    pd.DataFrame(
        [
            {
                "base_home_win_probability": 0.42,
                "base_draw_probability": 0.29,
                "base_away_probability": 0.29,
                "home_win_probability": 0.42,
                "draw_probability": 0.29,
                "away_win_probability": 0.29,
                "gd_adjusted_home_win_probability": 0.45,
                "gd_adjusted_draw_probability": 0.29,
                "gd_adjusted_away_probability": 0.26,
                "gf_adjusted_home_win_probability": 0.44,
                "gf_adjusted_draw_probability": 0.29,
                "gf_adjusted_away_probability": 0.27,
                "ga_adjusted_home_win_probability": 0.43,
                "ga_adjusted_draw_probability": 0.29,
                "ga_adjusted_away_probability": 0.28,
                "real_result": "HOME_WIN",
                "evaluation_result": "HIT",
            }
        ]
    ).to_csv(rows, index=False)

    result = analyze_promising_indicator_mix(rows, tmp_path / "out")

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
