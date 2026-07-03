import pandas as pd

from scripts.run_v2110_premier_league_2025_26_full_season_analysis import run_full_season_analysis


def test_v2110_full_season_safety_flags_false(tmp_path):
    fixtures = pd.DataFrame([{"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-16", "home_team": "Arsenal", "away_team": "Chelsea"}])

    def runner(**kwargs):
        return {
            "probability_analysis_status": "READY",
            "home_win_probability": 0.42,
            "draw_probability": 0.30,
            "away_win_probability": 0.28,
            "base_home_win_probability": 0.42,
            "base_draw_probability": 0.30,
            "base_away_probability": 0.28,
            "top_probability_outcome": "HOME",
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        }

    result = run_full_season_analysis(fixtures, output_dir=tmp_path, runner=runner)

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    rows = pd.read_csv(result["analysis_rows_csv_path"], keep_default_na=False)
    assert str(rows.loc[0, "automatic_betting_enabled"]).lower() == "false"
    assert str(rows.loc[0, "staking_logic_enabled"]).lower() == "false"
    assert str(rows.loc[0, "roi_logic_enabled"]).lower() == "false"
