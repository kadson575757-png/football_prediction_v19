import pandas as pd

from football_prediction_v19.analysis.v2109_attack_defense_matchup_indicator import build_attack_defense_matchup_indicator


def test_attack_defense_matchup_signals_and_excludes_match_date(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 3, "away_goals": 0},
        {"match_date": "2026-01-02", "home_team": "Arsenal", "away_team": "B", "home_goals": 2, "away_goals": 1},
        {"match_date": "2026-01-03", "home_team": "C", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-04", "home_team": "D", "away_team": "Chelsea", "home_goals": 3, "away_goals": 1},
        {"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2109_attack_defense_matchup_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_attack_defense_matchup_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["adm_home_home_goals_for_per_match"] == 2.5
    assert result["adm_away_away_goals_against_per_match"] == 2.5
    assert result["adm_home_attack_vs_away_defense_signal"] == 5.0
    assert result["adm_matchup_signal"] > 0
    assert round(result["adm_adjusted_home_win_probability"] + result["adm_adjusted_draw_probability"] + result["adm_adjusted_away_probability"], 6) == 1.0
