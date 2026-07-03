import pandas as pd

from football_prediction_v19.analysis.v2107_head_to_head_context_indicator import build_head_to_head_context_indicator


def test_head_to_head_context_indicator_counts_before_match_date(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2025-01-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
        {"match_date": "2025-02-01", "home_team": "Chelsea", "away_team": "Arsenal", "home_goals": 1, "away_goals": 2},
        {"match_date": "2025-03-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2107_head_to_head_context_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_head_to_head_context_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-01", 0.4, 0.3, 0.3)

    assert result["h2hc_matches_count"] == 3
    assert result["h2hc_home_team_wins_count"] == 2
    assert result["h2hc_away_team_wins_count"] == 0
    assert result["h2hc_draws_count"] == 1
    assert result["h2hc_home_team_win_rate"] == 0.6667
    assert result["h2hc_indicator_quality"] == "PARTIAL"


def test_head_to_head_context_low_quality_no_adjustment(monkeypatch):
    rows = pd.DataFrame([{"match_date": "2025-01-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0}])
    monkeypatch.setattr("football_prediction_v19.analysis.v2107_head_to_head_context_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_head_to_head_context_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-01", 0.4, 0.3, 0.3)

    assert result["h2hc_indicator_quality"] == "LOW"
    assert result["h2hc_adjustment_applied"] is False
    assert result["h2hc_adjusted_home_win_probability"] == 0.4
