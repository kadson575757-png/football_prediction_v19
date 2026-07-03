import pandas as pd

from football_prediction_v19.analysis.v2108_common_opponent_performance_indicator import build_common_opponent_performance_indicator


def test_common_opponent_performance_counts_common_opponents_and_excludes_match_date(monkeypatch):
    rows = []
    for i, opp in enumerate(["A", "B", "C"], start=1):
        rows.append({"match_date": f"2026-01-0{i}", "home_team": "Arsenal", "away_team": opp, "home_goals": 2, "away_goals": 0})
        rows.append({"match_date": f"2026-01-1{i}", "home_team": "Chelsea", "away_team": opp, "home_goals": 1, "away_goals": 1})
    rows.append({"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9})
    frame = pd.DataFrame(rows)
    monkeypatch.setattr("football_prediction_v19.analysis.v2108_common_opponent_performance_indicator._load_match_rows", lambda *args, **kwargs: frame)

    result = build_common_opponent_performance_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["cop_common_opponents_count"] == 3
    assert result["cop_home_points_vs_common_opponents"] == 9
    assert result["cop_away_points_vs_common_opponents"] == 3
    assert result["cop_home_ppg_vs_common_opponents"] == 3.0
    assert result["cop_goal_diff_gap_vs_common_opponents"] == 6
    assert result["cop_indicator_quality"] == "PARTIAL"


def test_common_opponent_low_quality_when_too_few_common_opponents(monkeypatch):
    frame = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-02", "home_team": "Chelsea", "away_team": "A", "home_goals": 1, "away_goals": 1},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2108_common_opponent_performance_indicator._load_match_rows", lambda *args, **kwargs: frame)

    result = build_common_opponent_performance_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["cop_indicator_quality"] == "LOW"
    assert result["cop_adjustment_applied"] is False
