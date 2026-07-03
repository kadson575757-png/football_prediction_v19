import pandas as pd

from football_prediction_v19.analysis.v2106_recent_goal_trend_indicator import build_recent_goal_trend_indicator


def test_recent_goal_trend_shadow_fields(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": f"2026-01-{i:02d}", "home_team": "Arsenal" if i % 2 else "Other", "away_team": "Other" if i % 2 else "Arsenal", "home_goals": 3 if i >= 6 and i % 2 else 1, "away_goals": 1 if i >= 6 and i % 2 else 0}
        for i in range(1, 11)
    ] + [
        {"match_date": f"2026-01-{i:02d}", "home_team": "Chelsea" if i % 2 else "Other", "away_team": "Other" if i % 2 else "Chelsea", "home_goals": 0, "away_goals": 2}
        for i in range(1, 11)
    ] + [{"match_date": "2026-01-11", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 9, "away_goals": 9}])
    monkeypatch.setattr("football_prediction_v19.analysis.v2106_recent_goal_trend_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_recent_goal_trend_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-11", 0.4, 0.3, 0.3)

    assert result["indicator_name"] == "RECENT_GOAL_TREND_PROFILE"
    assert result["rgt_home_attacking_trend"] != 0
    assert "rgt_net_trend_signal" in result
    assert result["rgt_adjustment_applied"] in {True, False}
    assert round(result["rgt_adjusted_home_win_probability"] + result["rgt_adjusted_draw_probability"] + result["rgt_adjusted_away_probability"], 6) == 1.0
