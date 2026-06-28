import pandas as pd

from scripts.analyze_v293_combined_shadow_mix import analyze_combined_shadow_mix


def test_v293_safety_flags_false(tmp_path):
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
                "ppg_adjusted_home_win_probability": 0.44,
                "ppg_adjusted_draw_probability": 0.29,
                "ppg_adjusted_away_probability": 0.27,
                "last5_adjusted_home_win_probability": 0.45,
                "last5_adjusted_draw_probability": 0.29,
                "last5_adjusted_away_probability": 0.26,
                "real_result": "HOME_WIN",
                "evaluation_result": "HIT",
            }
        ]
    ).to_csv(rows, index=False)

    result = analyze_combined_shadow_mix(rows, tmp_path / "out")

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
