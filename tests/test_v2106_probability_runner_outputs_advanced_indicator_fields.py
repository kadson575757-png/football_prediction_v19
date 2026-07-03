from football_prediction_v19.analysis.v2102_probability_output_schema import validate_probability_runner_output
from scripts.run_match_probability_analysis import run_match_probability_analysis
from tests.v25_test_helpers import fake_core_result


def _indicator(name, prefix, home=0.44, draw=0.30, away=0.26):
    return {
        "indicator_name": name,
        "indicator_quality": "FULL",
        "adjustment_applied": True,
        "adjusted_home_win_probability": home,
        "adjusted_draw_probability": draw,
        "adjusted_away_probability": away,
        f"{prefix}_indicator_quality": "FULL",
        f"{prefix}_adjusted_home_win_probability": home,
        f"{prefix}_adjusted_draw_probability": draw,
        f"{prefix}_adjusted_away_probability": away,
        f"{prefix}_adjustment_applied": True,
    }


def test_probability_runner_outputs_v2106_advanced_indicator_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    for name in ["build_home_away_ppg_indicator", "build_last5_form_indicator", "build_goal_difference_indicator", "build_goals_for_indicator", "build_goals_against_indicator"]:
        monkeypatch.setattr(f"scripts.run_match_winner_analysis.{name}", lambda *args, **kwargs: {})
    for name in ["build_draw_tendency_indicator", "build_venue_result_rate_indicator", "build_goal_margin_profile_indicator", "build_venue_scoring_balance_indicator"]:
        monkeypatch.setattr(f"scripts.run_match_probability_analysis.{name}", lambda **kwargs: _indicator(name.upper(), "dt", 0.43, 0.31, 0.26))
    for attr, indicator, prefix in [
        ("build_clean_sheet_failed_to_score_indicator", "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", "csfts"),
        ("build_rest_days_congestion_indicator", "REST_DAYS_CONGESTION_PROFILE", "rdc"),
        ("build_table_strength_gap_indicator", "TABLE_STRENGTH_GAP_PROFILE", "tsg"),
        ("build_comeback_blown_lead_indicator", "COMEBACK_BLOWN_LEAD_PROFILE", "cbl"),
        ("build_opponent_adjusted_recent_form_indicator", "OPPONENT_ADJUSTED_RECENT_FORM", "oarf"),
        ("build_recent_goal_trend_indicator", "RECENT_GOAL_TREND_PROFILE", "rgt"),
        ("build_venue_recent_momentum_indicator", "VENUE_RECENT_MOMENTUM_PROFILE", "vrm"),
        ("build_result_volatility_consistency_indicator", "RESULT_VOLATILITY_CONSISTENCY_PROFILE", "rvc"),
    ]:
        monkeypatch.setattr(f"scripts.run_match_probability_analysis.{attr}", lambda indicator=indicator, prefix=prefix, **kwargs: _indicator(indicator, prefix))

    result = run_match_probability_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-03-01", output_dir=tmp_path)

    assert result["oarf_adjusted_home_win_probability"] == 0.44
    assert result["rgt_adjusted_home_win_probability"] == 0.44
    assert result["vrm_adjusted_home_win_probability"] == 0.44
    assert result["rvc_adjusted_home_win_probability"] == 0.44
    assert "v2106_mix_adjusted_home_win_probability" in result
    assert "v2106_combined_mix_adjusted_home_win_probability" in result
    assert result["home_win_probability"] == result["base_home_win_probability"]
    assert result["draw_probability"] == result["base_draw_probability"]
    assert result["away_win_probability"] == result["base_away_probability"]
    assert validate_probability_runner_output(result)["schema_validation_status"] == "READY"
