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


def test_probability_runner_outputs_v2108_comparative_context_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    for name in ["build_home_away_ppg_indicator", "build_last5_form_indicator", "build_goal_difference_indicator", "build_goals_for_indicator", "build_goals_against_indicator"]:
        monkeypatch.setattr(f"scripts.run_match_winner_analysis.{name}", lambda *args, **kwargs: {})
    for attr, indicator, prefix in [
        ("build_draw_tendency_indicator", "DRAW_TENDENCY", "dt"), ("build_venue_result_rate_indicator", "VENUE_RESULT_RATE", "vr"),
        ("build_goal_margin_profile_indicator", "GOAL_MARGIN_PROFILE", "gm"), ("build_venue_scoring_balance_indicator", "VENUE_SCORING_BALANCE", "vsb"),
        ("build_clean_sheet_failed_to_score_indicator", "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", "csfts"), ("build_rest_days_congestion_indicator", "REST_DAYS_CONGESTION_PROFILE", "rdc"),
        ("build_table_strength_gap_indicator", "TABLE_STRENGTH_GAP_PROFILE", "tsg"), ("build_comeback_blown_lead_indicator", "COMEBACK_BLOWN_LEAD_PROFILE", "cbl"),
        ("build_opponent_adjusted_recent_form_indicator", "OPPONENT_ADJUSTED_RECENT_FORM", "oarf"), ("build_recent_goal_trend_indicator", "RECENT_GOAL_TREND_PROFILE", "rgt"),
        ("build_venue_recent_momentum_indicator", "VENUE_RECENT_MOMENTUM_PROFILE", "vrm"), ("build_result_volatility_consistency_indicator", "RESULT_VOLATILITY_CONSISTENCY_PROFILE", "rvc"),
        ("build_result_streak_indicator", "RESULT_STREAK_PROFILE", "rsp"), ("build_scoring_run_indicator", "SCORING_RUN_PROFILE", "srp"),
        ("build_head_to_head_context_indicator", "HEAD_TO_HEAD_CONTEXT_PROFILE", "h2hc"), ("build_league_zone_pressure_indicator", "LEAGUE_ZONE_PRESSURE_PROFILE", "lzp"),
        ("build_common_opponent_performance_indicator", "COMMON_OPPONENT_PERFORMANCE_PROFILE", "cop"), ("build_strength_band_performance_indicator", "STRENGTH_BAND_PERFORMANCE_PROFILE", "sbp"),
        ("build_response_after_result_indicator", "RESPONSE_AFTER_RESULT_PROFILE", "rar"), ("build_heavy_result_exposure_indicator", "HEAVY_RESULT_EXPOSURE_PROFILE", "hre"),
    ]:
        monkeypatch.setattr(f"scripts.run_match_probability_analysis.{attr}", lambda indicator=indicator, prefix=prefix, **kwargs: _indicator(indicator, prefix))

    result = run_match_probability_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-03-01", output_dir=tmp_path)

    assert result["cop_adjusted_home_win_probability"] == 0.44
    assert result["sbp_adjusted_home_win_probability"] == 0.44
    assert result["rar_adjusted_home_win_probability"] == 0.44
    assert result["hre_adjusted_home_win_probability"] == 0.44
    assert "v2108_mix_adjusted_home_win_probability" in result
    assert "v2108_combined_mix_adjusted_home_win_probability" in result
    assert result["home_win_probability"] == result["base_home_win_probability"]
    assert result["draw_probability"] == result["base_draw_probability"]
    assert result["away_win_probability"] == result["base_away_probability"]
    assert validate_probability_runner_output(result)["schema_validation_status"] == "READY"
    assert result["automatic_betting_enabled"] is False
