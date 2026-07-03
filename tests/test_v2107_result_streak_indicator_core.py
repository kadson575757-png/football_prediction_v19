import pandas as pd

from football_prediction_v19.analysis.v2107_result_streak_indicator import build_result_streak_indicator


def test_result_streak_indicator_counts_streaks_and_excludes_match_date(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-01-02", "home_team": "B", "away_team": "Arsenal", "home_goals": 0, "away_goals": 2},
        {"match_date": "2026-01-03", "home_team": "Arsenal", "away_team": "C", "home_goals": 3, "away_goals": 1},
        {"match_date": "2026-01-04", "home_team": "D", "away_team": "Chelsea", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-01-05", "home_team": "Chelsea", "away_team": "E", "home_goals": 0, "away_goals": 2},
        {"match_date": "2026-01-06", "home_team": "F", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-07", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2107_result_streak_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_result_streak_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-07", 0.4, 0.3, 0.3)

    assert result["rsp_home_win_streak"] == 2
    assert result["rsp_home_unbeaten_streak"] == 3
    assert result["rsp_away_loss_streak"] == 2
    assert result["rsp_away_winless_streak"] == 3
    assert result["rsp_streak_signal"] > 0
    assert round(result["rsp_adjusted_home_win_probability"] + result["rsp_adjusted_draw_probability"] + result["rsp_adjusted_away_probability"], 6) == 1.0
