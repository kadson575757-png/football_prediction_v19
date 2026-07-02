import pandas as pd

from football_prediction_v19.analysis import v2105_table_strength_gap_indicator as mod


def _rows():
    return pd.DataFrame(
        [{"match_date": f"2026-01-{d:02d}", "home_team": "Home", "away_team": f"X{d}", "home_goals": 2, "away_goals": 0} for d in range(1, 9)]
        + [{"match_date": f"2026-01-{d:02d}", "home_team": f"Y{d}", "away_team": "Away", "home_goals": 2, "away_goals": 0} for d in range(1, 9)]
        + [{"match_date": "2026-02-01", "home_team": "Home", "away_team": "Away", "home_goals": 0, "away_goals": 9}]
    )


def test_v2105_table_strength_gap_points_rank_and_excludes_match_date(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows())
    result = mod.build_table_strength_gap_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["tsg_indicator_quality"] == "FULL"
    assert result["tsg_home_points_before_match"] == 24
    assert result["tsg_away_points_before_match"] == 0
    assert result["tsg_home_points_per_match"] == 3.0
    assert result["tsg_away_points_per_match"] == 0.0
    assert result["tsg_rank_gap"] > 0
