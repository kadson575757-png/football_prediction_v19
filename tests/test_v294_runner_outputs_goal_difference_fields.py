from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v294_runner_outputs_goal_difference_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_home_away_ppg_indicator", lambda *args, **kwargs: {"indicator_quality": "LOW", "home_away_ppg_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_last5_form_indicator", lambda *args, **kwargs: {"last5_indicator_quality": "LOW", "last5_points_diff": 0})
    monkeypatch.setattr(
        "scripts.run_match_winner_analysis.build_goal_difference_indicator",
        lambda *args, **kwargs: {
            "goal_difference_indicator_quality": "FULL",
            "goal_difference_diff": 12,
            "home_matches_before_match": 10,
            "away_matches_before_match": 10,
            "home_goals_for_before_match": 25,
            "home_goals_against_before_match": 10,
            "away_goals_for_before_match": 18,
            "away_goals_against_before_match": 15,
            "home_goal_difference_before_match": 15,
            "away_goal_difference_before_match": 3,
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
    assert "gd_adjusted_home_win_probability" in result
    assert "gd_adjusted_draw_probability" in result
    assert "gd_adjusted_away_probability" in result
    assert result["home_win_probability"] == result["base_home_win_probability"]
    assert result["draw_probability"] == result["base_draw_probability"]
    assert result["away_win_probability"] == result["base_away_probability"]
    assert result["gd_adjusted_home_win_probability"] != result["base_home_win_probability"]
    assert result["home_goal_difference_before_match"] == 15
    assert result["away_goal_difference_before_match"] == 3
    assert result["goal_difference_diff"] == 12
    assert result["goal_difference_indicator_quality"] == "FULL"
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
