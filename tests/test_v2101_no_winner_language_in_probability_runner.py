from scripts import run_match_probability_analysis


def test_v2101_probability_runner_hides_winner_language(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        "scripts.run_match_probability_analysis.run_match_winner_analysis",
        lambda **kwargs: {
            "winner_analysis_status": "READY",
            "decision_class": "PROBABILITY_ONLY",
            "predicted_winner": "",
            "probability_model_status": "READY",
            "top_probability_outcome": "HOME",
            "probability_edge": 0.12,
            "probability_edge_band": "LARGE",
            "uncertainty_level": "LOW",
            "data_quality_band": "HIGH",
            "probability_summary": "HOME has the highest probability.",
            "data_quality_notes": ["Core source coverage is sufficient."],
            "home_win_probability": 0.48,
            "draw_probability": 0.27,
            "away_win_probability": 0.25,
            "base_home_win_probability": 0.48,
            "base_draw_probability": 0.27,
            "base_away_probability": 0.25,
            "prediction_tier": "legacy",
            "risk_notes": "legacy",
        },
    )

    assert run_match_probability_analysis.main(
        [
            "--competition", "Premier League",
            "--season", "2025/26",
            "--home", "Arsenal",
            "--away", "Chelsea",
            "--match-date", "2026-03-01",
            "--output-dir", str(tmp_path),
        ]
    ) == 0
    output = capsys.readouterr().out

    for token in [
        "winner_analysis_status",
        "decision_class",
        "predicted_winner",
        "winner_pick",
        "winner_lean",
        "NO_DECISION",
        "DATA_BLOCKED",
        "blocked by rule",
        "Lean-only",
        "decision strength",
        "prediction_tier",
        "risk_notes",
    ]:
        assert token not in output
