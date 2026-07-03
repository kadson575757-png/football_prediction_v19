import pandas as pd

from football_prediction_v19.analysis.v2108_heavy_result_exposure_indicator import build_heavy_result_exposure_indicator


def test_heavy_result_exposure_rates_and_probability_sum(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 4, "away_goals": 0},
        {"match_date": "2026-01-02", "home_team": "B", "away_team": "Arsenal", "home_goals": 0, "away_goals": 2},
        {"match_date": "2026-01-03", "home_team": "Arsenal", "away_team": "C", "home_goals": 1, "away_goals": 0},
        {"match_date": "2026-01-04", "home_team": "Chelsea", "away_team": "D", "home_goals": 0, "away_goals": 3},
        {"match_date": "2026-01-05", "home_team": "E", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-06", "home_team": "Chelsea", "away_team": "F", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2108_heavy_result_exposure_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_heavy_result_exposure_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["hre_home_big_win_rate"] == 0.3333
    assert result["hre_away_big_loss_rate"] == 0.3333
    assert "hre_heavy_result_signal" in result
    assert round(result["hre_adjusted_home_win_probability"] + result["hre_adjusted_draw_probability"] + result["hre_adjusted_away_probability"], 6) == 1.0
