from scripts import run_match_probability_analysis


def test_v2101_probability_runner_alias_outputs_probability_fields(monkeypatch, tmp_path, capsys):
    assert run_match_probability_analysis.Path("scripts/run_match_probability_analysis.py").exists()

    monkeypatch.setattr(
        "scripts.run_match_probability_analysis.run_match_winner_analysis",
        lambda **kwargs: {
            "probability_model_status": "READY",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "top_probability_outcome": "HOME",
            "probability_edge": 0.12,
            "probability_edge_band": "LARGE",
            "uncertainty_level": "LOW",
            "data_quality_band": "HIGH",
            "probability_explanation_status": "READY",
            "probability_summary": "HOME has the highest probability.",
            "data_quality_notes": ["Core source coverage is sufficient."],
            "home_win_probability": 0.48,
            "draw_probability": 0.27,
            "away_win_probability": 0.25,
            "base_home_win_probability": 0.48,
            "base_draw_probability": 0.27,
            "base_away_probability": 0.25,
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        },
    )

    exit_code = run_match_probability_analysis.main(
        [
            "--competition", "Premier League",
            "--season", "2025/26",
            "--home", "Arsenal",
            "--away", "Chelsea",
            "--match-date", "2026-03-01",
            "--output-dir", str(tmp_path),
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "probability_analysis_status=READY" in output
    assert "probability_model_status=READY" in output
    assert "home_win_probability=0.48" in output
    assert "draw_probability=0.27" in output
    assert "away_win_probability=0.25" in output
    assert "top_probability_outcome=HOME" in output
    assert "probability_summary=HOME has the highest probability." in output
    assert "automatic_betting_enabled=false" in output
    assert "staking_logic_enabled=false" in output
    assert "roi_logic_enabled=false" in output
