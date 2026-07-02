from scripts.run_match_probability_analysis import run_match_probability_analysis
from tests.v25_test_helpers import fake_core_result


def test_v2104_probability_runner_outputs_multi_indicator_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    for name in [
        "build_home_away_ppg_indicator",
        "build_last5_form_indicator",
        "build_goal_difference_indicator",
        "build_goals_for_indicator",
        "build_goals_against_indicator",
    ]:
        monkeypatch.setattr(f"scripts.run_match_winner_analysis.{name}", lambda *args, **kwargs: {})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_draw_tendency_indicator", lambda **kwargs: {"indicator_name": "DRAW_TENDENCY", "indicator_quality": "FULL", "adjustment_applied": True, "adjusted_home_win_probability": 0.38, "adjusted_draw_probability": 0.36, "adjusted_away_probability": 0.26, "dt_adjusted_draw_probability": 0.36, "dt_indicator_quality": "FULL"})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_venue_result_rate_indicator", lambda **kwargs: {"indicator_name": "VENUE_RESULT_RATE", "indicator_quality": "FULL", "adjustment_applied": True, "adjusted_home_win_probability": 0.45, "adjusted_draw_probability": 0.29, "adjusted_away_probability": 0.26, "vr_adjusted_home_win_probability": 0.45, "vr_indicator_quality": "FULL"})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_goal_margin_profile_indicator", lambda **kwargs: {"indicator_name": "GOAL_MARGIN_PROFILE", "indicator_quality": "FULL", "adjustment_applied": True, "adjusted_home_win_probability": 0.44, "adjusted_draw_probability": 0.3, "adjusted_away_probability": 0.26, "gm_adjusted_home_win_probability": 0.44, "gm_indicator_quality": "FULL"})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_venue_scoring_balance_indicator", lambda **kwargs: {"indicator_name": "VENUE_SCORING_BALANCE", "indicator_quality": "FULL", "adjustment_applied": True, "adjusted_home_win_probability": 0.43, "adjusted_draw_probability": 0.3, "adjusted_away_probability": 0.27, "vsb_adjusted_home_win_probability": 0.43, "vsb_indicator_quality": "FULL"})

    result = run_match_probability_analysis(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )

    assert result["dt_adjusted_draw_probability"] == 0.36
    assert result["vr_adjusted_home_win_probability"] == 0.45
    assert result["gm_adjusted_home_win_probability"] == 0.44
    assert result["vsb_adjusted_home_win_probability"] == 0.43
    assert "mix_adjusted_home_win_probability" in result
    assert "mix_adjusted_draw_probability" in result
    assert "mix_adjusted_away_probability" in result
    assert result["mix_included_indicators"]
    assert result["mix_shadow_explanation"]
    assert result["home_win_probability"] == result["base_home_win_probability"]
    assert result["draw_probability"] == result["base_draw_probability"]
    assert result["away_win_probability"] == result["base_away_probability"]
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
