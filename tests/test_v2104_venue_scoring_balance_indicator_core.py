import pandas as pd

from football_prediction_v19.analysis import v2104_venue_scoring_balance_indicator as mod


def _rows():
    return pd.DataFrame(
        [{"match_date": f"2026-01-{day:02d}", "home_team": "Home", "away_team": f"X{day}", "home_goals": 3, "away_goals": 1} for day in range(1, 9)]
        + [{"match_date": f"2026-01-{day:02d}", "home_team": f"Y{day}", "away_team": "Away", "home_goals": 2, "away_goals": 1} for day in range(1, 9)]
    )


def test_v2104_venue_scoring_balance_rates_and_pressure(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows())
    result = mod.build_venue_scoring_balance_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["vsb_indicator_quality"] == "FULL"
    assert result["vsb_home_home_goals_for_per_match"] == 3.0
    assert result["vsb_home_home_goals_against_per_match"] == 1.0
    assert result["vsb_away_away_goals_for_per_match"] == 1.0
    assert result["vsb_away_away_goals_against_per_match"] == 2.0
    assert result["vsb_goal_pressure_diff"] > 0
    assert round(result["vsb_adjusted_home_win_probability"] + result["vsb_adjusted_draw_probability"] + result["vsb_adjusted_away_probability"], 4) == 1.0
