import pandas as pd

from football_prediction_v19.analysis import v2105_rest_days_congestion_indicator as mod


def _rows():
    home = [{"match_date": f"2026-01-{d:02d}", "home_team": "Home", "away_team": f"X{d}", "home_goals": 1, "away_goals": 0} for d in [1, 4, 8, 12, 16, 20, 24, 25]]
    away = [{"match_date": f"2026-01-{d:02d}", "home_team": f"Y{d}", "away_team": "Away", "home_goals": 0, "away_goals": 1} for d in [1, 5, 9, 13, 17, 21, 26, 30]]
    return pd.DataFrame(home + away + [{"match_date": "2026-02-01", "home_team": "Home", "away_team": "Away", "home_goals": 9, "away_goals": 0}])


def test_v2105_rest_days_congestion_counts_and_excludes_match_date(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows())
    result = mod.build_rest_days_congestion_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["rdc_indicator_quality"] == "FULL"
    assert result["rdc_home_days_since_last_match"] == 7
    assert result["rdc_away_days_since_last_match"] == 2
    assert result["rdc_rest_days_diff"] == 5
    assert result["rdc_home_matches_last_14_days"] == 3
    assert result["rdc_away_matches_last_14_days"] == 3
