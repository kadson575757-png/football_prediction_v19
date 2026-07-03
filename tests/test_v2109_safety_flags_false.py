from scripts.run_match_probability_analysis import run_match_probability_analysis
from tests.v25_test_helpers import fake_core_result


def test_v2109_probability_runner_keeps_safety_flags_false(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    for name in ["build_home_away_ppg_indicator", "build_last5_form_indicator", "build_goal_difference_indicator", "build_goals_for_indicator", "build_goals_against_indicator"]:
        monkeypatch.setattr(f"scripts.run_match_winner_analysis.{name}", lambda *args, **kwargs: {})
    for name in [
        "build_draw_tendency_indicator", "build_venue_result_rate_indicator", "build_goal_margin_profile_indicator", "build_venue_scoring_balance_indicator",
        "build_clean_sheet_failed_to_score_indicator", "build_rest_days_congestion_indicator", "build_table_strength_gap_indicator", "build_comeback_blown_lead_indicator",
        "build_opponent_adjusted_recent_form_indicator", "build_recent_goal_trend_indicator", "build_venue_recent_momentum_indicator", "build_result_volatility_consistency_indicator",
        "build_result_streak_indicator", "build_scoring_run_indicator", "build_head_to_head_context_indicator", "build_league_zone_pressure_indicator",
        "build_common_opponent_performance_indicator", "build_strength_band_performance_indicator", "build_response_after_result_indicator", "build_heavy_result_exposure_indicator",
        "build_attack_defense_matchup_indicator", "build_venue_split_delta_indicator", "build_draw_pressure_composite_indicator",
    ]:
        monkeypatch.setattr(f"scripts.run_match_probability_analysis.{name}", lambda **kwargs: {})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_shadow_consensus_alignment_indicator", lambda *args, **kwargs: {})

    result = run_match_probability_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-03-01", output_dir=tmp_path)

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert "profit" not in result
    assert "yield" not in result
    assert "bankroll" not in result
