import pandas as pd

from football_prediction_v19.analysis.v2109_draw_pressure_composite_indicator import build_draw_pressure_composite_indicator


def test_draw_pressure_composite_rates_signal_and_probability_sum(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-01-02", "home_team": "B", "away_team": "Arsenal", "home_goals": 0, "away_goals": 1},
        {"match_date": "2026-01-03", "home_team": "Arsenal", "away_team": "C", "home_goals": 2, "away_goals": 1},
        {"match_date": "2026-01-04", "home_team": "Chelsea", "away_team": "D", "home_goals": 0, "away_goals": 0},
        {"match_date": "2026-01-05", "home_team": "E", "away_team": "Chelsea", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-01-06", "home_team": "Chelsea", "away_team": "F", "home_goals": 1, "away_goals": 0},
        {"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2109_draw_pressure_composite_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_draw_pressure_composite_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-01", 0.36, 0.34, 0.30)

    assert result["dpc_home_draw_rate"] == 0.3333
    assert result["dpc_away_draw_rate"] == 0.6667
    assert result["dpc_combined_draw_rate"] == 0.5
    assert result["dpc_combined_narrow_match_rate"] == 1.0
    assert result["dpc_base_probability_edge"] == 0.02
    assert result["dpc_draw_pressure_signal"] > 0
    assert round(result["dpc_adjusted_home_win_probability"] + result["dpc_adjusted_draw_probability"] + result["dpc_adjusted_away_probability"], 6) == 1.0
