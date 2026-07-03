import pandas as pd

from football_prediction_v19.analysis.v2107_scoring_run_indicator import build_scoring_run_indicator


def test_scoring_run_indicator_counts_runs_and_excludes_match_date(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-02", "home_team": "B", "away_team": "Arsenal", "home_goals": 1, "away_goals": 2},
        {"match_date": "2026-01-03", "home_team": "Arsenal", "away_team": "C", "home_goals": 3, "away_goals": 1},
        {"match_date": "2026-01-04", "home_team": "Chelsea", "away_team": "D", "home_goals": 0, "away_goals": 2},
        {"match_date": "2026-01-05", "home_team": "E", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-06", "home_team": "Chelsea", "away_team": "F", "home_goals": 0, "away_goals": 1},
        {"match_date": "2026-01-07", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2107_scoring_run_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_scoring_run_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-07", 0.4, 0.3, 0.3)

    assert result["srp_home_scored_streak"] == 3
    assert result["srp_home_conceded_streak"] == 2
    assert result["srp_away_failed_to_score_streak"] == 3
    assert result["srp_away_conceded_streak"] == 3
    assert result["srp_home_scoring_run_signal"] > result["srp_away_scoring_run_signal"]
    assert round(result["srp_adjusted_home_win_probability"] + result["srp_adjusted_draw_probability"] + result["srp_adjusted_away_probability"], 6) == 1.0
