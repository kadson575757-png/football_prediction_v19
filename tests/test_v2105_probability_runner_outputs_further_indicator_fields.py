from football_prediction_v19.analysis.v2102_probability_output_schema import validate_probability_runner_output
from scripts.run_match_probability_analysis import run_match_probability_analysis
from tests.v25_test_helpers import fake_core_result


def test_v2105_probability_runner_outputs_further_indicator_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    for name in ["build_home_away_ppg_indicator", "build_last5_form_indicator", "build_goal_difference_indicator", "build_goals_for_indicator", "build_goals_against_indicator"]:
        monkeypatch.setattr(f"scripts.run_match_winner_analysis.{name}", lambda *args, **kwargs: {})
    for name in ["build_draw_tendency_indicator", "build_venue_result_rate_indicator", "build_goal_margin_profile_indicator", "build_venue_scoring_balance_indicator"]:
        monkeypatch.setattr(f"scripts.run_match_probability_analysis.{name}", lambda **kwargs: {"indicator_name": name.upper(), "indicator_quality": "LOW", "adjustment_applied": False, "adjusted_home_win_probability": 0.43, "adjusted_draw_probability": 0.31, "adjusted_away_probability": 0.26})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_clean_sheet_failed_to_score_indicator", lambda **kwargs: {"indicator_name": "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE", "indicator_quality": "FULL", "adjustment_applied": True, "adjusted_home_win_probability": 0.45, "adjusted_draw_probability": 0.29, "adjusted_away_probability": 0.26, "csfts_adjusted_home_win_probability": 0.45, "csfts_indicator_quality": "FULL"})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_rest_days_congestion_indicator", lambda **kwargs: {"indicator_name": "REST_DAYS_CONGESTION_PROFILE", "indicator_quality": "FULL", "adjustment_applied": True, "adjusted_home_win_probability": 0.44, "adjusted_draw_probability": 0.30, "adjusted_away_probability": 0.26, "rdc_adjusted_home_win_probability": 0.44, "rdc_indicator_quality": "FULL"})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_table_strength_gap_indicator", lambda **kwargs: {"indicator_name": "TABLE_STRENGTH_GAP_PROFILE", "indicator_quality": "FULL", "adjustment_applied": True, "adjusted_home_win_probability": 0.46, "adjusted_draw_probability": 0.28, "adjusted_away_probability": 0.26, "tsg_adjusted_home_win_probability": 0.46, "tsg_indicator_quality": "FULL"})
    monkeypatch.setattr("scripts.run_match_probability_analysis.build_comeback_blown_lead_indicator", lambda **kwargs: {"indicator_name": "COMEBACK_BLOWN_LEAD_PROFILE", "indicator_quality": "LOW", "adjustment_applied": False, "adjusted_home_win_probability": 0.43, "adjusted_draw_probability": 0.31, "adjusted_away_probability": 0.26, "cbl_adjusted_home_win_probability": 0.43, "cbl_indicator_quality": "LOW"})

    result = run_match_probability_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-03-01", output_dir=tmp_path)

    assert result["csfts_adjusted_home_win_probability"] == 0.45
    assert result["rdc_adjusted_home_win_probability"] == 0.44
    assert result["tsg_adjusted_home_win_probability"] == 0.46
    assert result["cbl_adjusted_home_win_probability"] == 0.43
    assert "v2105_mix_adjusted_home_win_probability" in result
    assert "combined_mix_adjusted_home_win_probability" in result
    assert result["home_win_probability"] == result["base_home_win_probability"]
    assert result["draw_probability"] == result["base_draw_probability"]
    assert result["away_win_probability"] == result["base_away_probability"]
    assert validate_probability_runner_output(result)["schema_validation_status"] == "READY"
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
