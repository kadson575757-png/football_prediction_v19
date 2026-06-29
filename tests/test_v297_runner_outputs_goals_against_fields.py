from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v297_runner_outputs_goals_against_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_home_away_ppg_indicator", lambda *args, **kwargs: {"indicator_quality": "LOW", "home_away_ppg_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_last5_form_indicator", lambda *args, **kwargs: {"last5_indicator_quality": "LOW", "last5_points_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goal_difference_indicator", lambda *args, **kwargs: {"goal_difference_indicator_quality": "LOW", "goal_difference_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_for_indicator", lambda *args, **kwargs: {"goals_for_indicator_quality": "LOW", "goals_for_per_match_diff": 0})
    monkeypatch.setattr(
        "scripts.run_match_winner_analysis.build_goals_against_indicator",
        lambda *args, **kwargs: {
            "goals_against_indicator_quality": "FULL",
            "goals_against_advantage_diff": 0.5,
            "home_goals_against_before_match": 10,
            "away_goals_against_before_match": 18,
            "home_goals_against_per_match_before_match": 1.0,
            "away_goals_against_per_match_before_match": 1.8,
        },
    )

    result = run_match_winner_analysis(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )

    assert "base_home_win_probability" in result
    assert "ga_adjusted_home_win_probability" in result
    assert "ga_adjusted_draw_probability" in result
    assert "ga_adjusted_away_probability" in result
    assert result["home_win_probability"] == result["base_home_win_probability"]
    assert result["draw_probability"] == result["base_draw_probability"]
    assert result["away_win_probability"] == result["base_away_probability"]
    assert result["ga_adjusted_home_win_probability"] != result["base_home_win_probability"]
    assert result["home_goals_against_before_match"] == 10
    assert result["away_goals_against_before_match"] == 18
    assert result["goals_against_advantage_diff"] == 0.5
    assert result["goals_against_indicator_quality"] == "FULL"
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
