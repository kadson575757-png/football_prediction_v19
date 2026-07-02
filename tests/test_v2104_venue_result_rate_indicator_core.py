import pandas as pd

from football_prediction_v19.analysis import v2104_venue_result_rate_indicator as mod


def _rows():
    home = [{"match_date": f"2026-01-{day:02d}", "home_team": "Home", "away_team": f"X{day}", "home_goals": 2, "away_goals": 0} for day in range(1, 7)]
    home += [{"match_date": f"2026-01-{day:02d}", "home_team": "Home", "away_team": f"X{day}", "home_goals": 1, "away_goals": 1} for day in range(7, 9)]
    away = [{"match_date": f"2026-01-{day:02d}", "home_team": f"Y{day}", "away_team": "Away", "home_goals": 1, "away_goals": 3} for day in range(1, 3)]
    away += [{"match_date": f"2026-01-{day:02d}", "home_team": f"Y{day}", "away_team": "Away", "home_goals": 2, "away_goals": 2} for day in range(3, 5)]
    away += [{"match_date": f"2026-01-{day:02d}", "home_team": f"Y{day}", "away_team": "Away", "home_goals": 2, "away_goals": 0} for day in range(5, 9)]
    return pd.DataFrame(home + away + [{"match_date": "2026-02-01", "home_team": "Home", "away_team": "Away", "home_goals": 0, "away_goals": 9}])


def test_v2104_venue_result_rates_signals_and_excludes_match_date(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows())
    result = mod.build_venue_result_rate_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["vr_indicator_quality"] == "FULL"
    assert result["vr_home_home_win_rate"] == 0.75
    assert result["vr_home_home_draw_rate"] == 0.25
    assert result["vr_away_away_win_rate"] == 0.25
    assert result["vr_away_away_draw_rate"] == 0.25
    assert result["vr_home_signal"] > result["vr_away_signal"]
    assert result["vr_adjusted_home_win_probability"] > 0.4
