import pandas as pd

from football_prediction_v19.analysis import v2104_goal_margin_profile_indicator as mod


def _rows():
    return pd.DataFrame(
        [{"match_date": f"2026-01-{day:02d}", "home_team": "Home", "away_team": f"X{day}", "home_goals": 2, "away_goals": 1} for day in range(1, 9)]
        + [{"match_date": f"2026-01-{day:02d}", "home_team": f"Y{day}", "away_team": "Away", "home_goals": 1, "away_goals": 0} for day in range(1, 9)]
        + [{"match_date": "2026-02-01", "home_team": "Home", "away_team": "Away", "home_goals": 8, "away_goals": 0}]
    )


def test_v2104_goal_margin_and_narrow_rates(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows())
    result = mod.build_goal_margin_profile_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["gm_indicator_quality"] == "FULL"
    assert result["gm_home_average_goal_margin"] == 1.0
    assert result["gm_away_average_goal_margin"] == -1.0
    assert result["gm_combined_narrow_match_rate"] == 1.0
    assert round(result["gm_adjusted_home_win_probability"] + result["gm_adjusted_draw_probability"] + result["gm_adjusted_away_probability"], 4) == 1.0
