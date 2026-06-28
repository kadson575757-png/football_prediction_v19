from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v292_safety_flags_false(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_home_away_ppg_indicator", lambda *args, **kwargs: {"indicator_quality": "LOW", "home_away_ppg_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_last5_form_indicator", lambda *args, **kwargs: {"last5_indicator_quality": "LOW", "last5_points_diff": 0})

    result = run_match_winner_analysis(
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
