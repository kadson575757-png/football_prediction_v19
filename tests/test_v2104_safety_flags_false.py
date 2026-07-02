from scripts.run_match_probability_analysis import run_match_probability_analysis
from tests.v25_test_helpers import fake_core_result


def test_v2104_safety_flags_false(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    for name in [
        "build_home_away_ppg_indicator",
        "build_last5_form_indicator",
        "build_goal_difference_indicator",
        "build_goals_for_indicator",
        "build_goals_against_indicator",
    ]:
        monkeypatch.setattr(f"scripts.run_match_winner_analysis.{name}", lambda *args, **kwargs: {})
    for name in [
        "build_draw_tendency_indicator",
        "build_venue_result_rate_indicator",
        "build_goal_margin_profile_indicator",
        "build_venue_scoring_balance_indicator",
    ]:
        monkeypatch.setattr(f"scripts.run_match_probability_analysis.{name}", lambda **kwargs: {"indicator_name": name.upper(), "indicator_quality": "LOW", "adjustment_applied": False, "adjusted_home_win_probability": 0.43, "adjusted_draw_probability": 0.31, "adjusted_away_probability": 0.26})

    result = run_match_probability_analysis(
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
