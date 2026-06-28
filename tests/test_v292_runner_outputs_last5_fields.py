from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v292_runner_outputs_last5_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    monkeypatch.setattr(
        "scripts.run_match_winner_analysis.build_home_away_ppg_indicator",
        lambda *args, **kwargs: {"indicator_quality": "FULL", "home_away_ppg_diff": 0.0, "home_home_ppg_before_match": 2.0, "away_away_ppg_before_match": 1.2},
    )
    monkeypatch.setattr(
        "scripts.run_match_winner_analysis.build_last5_form_indicator",
        lambda *args, **kwargs: {"last5_indicator_quality": "FULL", "last5_points_diff": 6, "home_last5_points": 12, "away_last5_points": 6, "home_last5_points_per_match": 2.4, "away_last5_points_per_match": 1.2},
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
    assert "last5_adjusted_home_win_probability" in result
    assert "last5_adjusted_draw_probability" in result
    assert "last5_adjusted_away_probability" in result
    assert result["home_win_probability"] == result["base_home_win_probability"]
    assert result["draw_probability"] == result["base_draw_probability"]
    assert result["away_win_probability"] == result["base_away_probability"]
    assert result["last5_adjusted_home_win_probability"] != result["base_home_win_probability"]
    assert result["home_last5_points"] == 12
    assert result["away_last5_points"] == 6
    assert result["last5_points_diff"] == 6
    assert result["last5_indicator_quality"] == "FULL"
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
