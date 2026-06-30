from scripts.run_match_probability_analysis import run_match_probability_analysis


def test_v2101_probability_runner_safety_flags_false(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "scripts.run_match_probability_analysis.run_match_winner_analysis",
        lambda **kwargs: {
            "probability_model_status": "READY",
            "home_win_probability": 0.48,
            "draw_probability": 0.27,
            "away_win_probability": 0.25,
            "base_home_win_probability": 0.48,
            "base_draw_probability": 0.27,
            "base_away_probability": 0.25,
            "automatic_betting_enabled": True,
            "staking_logic_enabled": True,
            "roi_logic_enabled": True,
        },
    )

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
