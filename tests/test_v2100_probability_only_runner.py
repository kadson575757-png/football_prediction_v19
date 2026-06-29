from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def _patch_shadows(monkeypatch):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_home_away_ppg_indicator", lambda *args, **kwargs: {"indicator_quality": "LOW", "home_away_ppg_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_last5_form_indicator", lambda *args, **kwargs: {"last5_indicator_quality": "LOW", "last5_points_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goal_difference_indicator", lambda *args, **kwargs: {"goal_difference_indicator_quality": "FULL", "goal_difference_diff": 18})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_for_indicator", lambda *args, **kwargs: {"goals_for_indicator_quality": "FULL", "goals_for_per_match_diff": 0.22})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_against_indicator", lambda *args, **kwargs: {"goals_against_indicator_quality": "FULL", "goals_against_advantage_diff": 0.4})


def test_v2100_runner_always_outputs_probabilities(monkeypatch, tmp_path):
    _patch_shadows(monkeypatch)

    result = run_match_winner_analysis(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )

    assert result["winner_analysis_status"] == "READY"
    assert result["decision_class"] != "NO_DECISION"
    assert result["decision_class"] != "DATA_BLOCKED"
    assert result["home_win_probability"] > 0
    assert result["draw_probability"] > 0
    assert result["away_win_probability"] > 0
    assert result["base_home_win_probability"] == result["home_win_probability"]
    assert result["top_probability_outcome"] == "HOME"
    assert result["probability_edge"] > 0
    assert result["probability_edge_band"] in {"VERY_SMALL", "SMALL", "MEDIUM", "LARGE"}
    assert result["uncertainty_level"] in {"LOW", "MEDIUM", "HIGH"}


def test_v2100_small_edge_does_not_create_data_block(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result(decision_class="NO_DECISION", predicted_winner=""))
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_home_away_ppg_indicator", lambda *args, **kwargs: {"indicator_quality": "LOW", "home_away_ppg_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_last5_form_indicator", lambda *args, **kwargs: {"last5_indicator_quality": "LOW", "last5_points_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goal_difference_indicator", lambda *args, **kwargs: {"goal_difference_indicator_quality": "LOW", "goal_difference_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_for_indicator", lambda *args, **kwargs: {"goals_for_indicator_quality": "LOW", "goals_for_per_match_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_against_indicator", lambda *args, **kwargs: {"goals_against_indicator_quality": "LOW", "goals_against_advantage_diff": 0})

    result = run_match_winner_analysis(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )

    assert result["winner_analysis_status"] == "READY"
    assert result["decision_class"] == "PROBABILITY_ONLY"
    assert result["probability_model_status"] in {"READY", "READY_WITH_LIMITATIONS"}
    assert result["top_probability_outcome"] in {"HOME", "DRAW", "AWAY"}
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
