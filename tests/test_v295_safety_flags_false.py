import pandas as pd

from scripts import audit_v295_goal_difference_sources as mod


def test_v295_safety_flags_false(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mod,
        "_load_match_rows",
        lambda *args, **kwargs: pd.DataFrame(
            [
                {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 1, "away_goals": 0},
                {"match_date": "2026-02-20", "home_team": "Chelsea", "away_team": "Team B", "home_goals": 0, "away_goals": 1},
            ]
        ),
    )

    result = mod.audit_goal_difference_sources(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
