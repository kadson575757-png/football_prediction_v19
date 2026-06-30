from scripts import run_match_probability_analysis
from football_prediction_v19.analysis.v2102_probability_output_schema import (
    FORBIDDEN_PROBABILITY_RUNNER_FIELDS,
    FORBIDDEN_PROBABILITY_RUNNER_TEXT_PATTERNS,
    REQUIRED_PROBABILITY_RUNNER_FIELDS,
    validate_probability_runner_output,
)


def test_v2102_probability_runner_schema_lock(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        "scripts.run_match_probability_analysis.run_match_winner_analysis",
        lambda **kwargs: _clean_runner_output(),
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
    output = _parse_console(capsys.readouterr().out)
    validation = validate_probability_runner_output(output)

    assert validation["schema_validation_status"] == "READY"
    assert all(field in output for field in REQUIRED_PROBABILITY_RUNNER_FIELDS)
    assert not any(field in output for field in FORBIDDEN_PROBABILITY_RUNNER_FIELDS)
    assert not any(pattern in "\n".join(output.values()) for pattern in FORBIDDEN_PROBABILITY_RUNNER_TEXT_PATTERNS)
    assert output["automatic_betting_enabled"] == "false"
    assert output["staking_logic_enabled"] == "false"
    assert output["roi_logic_enabled"] == "false"
    assert output["home_win_probability"]
    assert output["draw_probability"]
    assert output["away_win_probability"]


def _clean_runner_output() -> dict[str, object]:
    return {
        "probability_model_status": "READY",
        "competition": "Premier League",
        "season": "2025/26",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "match_date": "2026-03-01",
        "top_probability_outcome": "HOME",
        "probability_edge": 0.12,
        "probability_edge_band": "LARGE",
        "uncertainty_level": "LOW",
        "data_quality_band": "HIGH",
        "probability_explanation_status": "READY",
        "probability_summary": "HOME has the highest probability.",
        "data_quality_notes": ["Core source coverage is sufficient."],
        "probability_input_signals": ["base probability"],
        "home_win_probability": 0.48,
        "draw_probability": 0.27,
        "away_win_probability": 0.25,
        "base_home_win_probability": 0.48,
        "base_draw_probability": 0.27,
        "base_away_probability": 0.25,
        "base_probability_explanation": "Base probability output is ready.",
        "probability_explanation": "HOME is the highest probability outcome.",
        "data_quality_explanation": "Core sources are available.",
        "final_probability_explanation": "Final probabilities remain base probabilities.",
        "signal_alignment_summary": "Signals support the top probability.",
        "signal_conflict_summary": "No material signal conflict.",
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _parse_console(text: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
