from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v2100_explanation_fields_describe_limitations_without_blocking(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_home_away_ppg_indicator", lambda *args, **kwargs: {"indicator_quality": "LOW", "home_away_ppg_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_last5_form_indicator", lambda *args, **kwargs: {"last5_indicator_quality": "LOW", "last5_points_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goal_difference_indicator", lambda *args, **kwargs: {"goal_difference_indicator_quality": "FULL", "goal_difference_diff": 12})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_for_indicator", lambda *args, **kwargs: {"goals_for_indicator_quality": "FULL", "goals_for_per_match_diff": 0.3})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_against_indicator", lambda *args, **kwargs: {"goals_against_indicator_quality": "FULL", "goals_against_advantage_diff": 0.2})

    result = run_match_winner_analysis(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )

    for key in [
        "base_probability_explanation",
        "ppg_shadow_explanation",
        "last5_shadow_explanation",
        "goal_difference_shadow_explanation",
        "goals_for_shadow_explanation",
        "goals_against_shadow_explanation",
        "signal_alignment_summary",
        "signal_conflict_summary",
        "data_quality_explanation",
        "final_probability_explanation",
    ]:
        assert result[key]
    assert "Probability output is still produced" in result["data_quality_explanation"]
    assert "Shadow indicators are shown separately" in result["final_probability_explanation"]
    assert "blocked by rule" not in result["probability_explanation"].lower()
