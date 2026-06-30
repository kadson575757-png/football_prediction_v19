from scripts import run_v27_prematch_evaluation
from football_prediction_v19.analysis.v2102_probability_output_schema import (
    FORBIDDEN_PROBABILITY_EVALUATION_FIELDS,
    REQUIRED_PROBABILITY_EVALUATION_FIELDS,
    validate_probability_evaluation_output,
)


def test_v2102_probability_evaluation_schema_lock(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.run_v27_prematch_evaluation.run_prematch_evaluation",
        lambda **kwargs: {
            "v27_prematch_evaluation_status": "READY",
            "matches_requested": 40,
            "matches_evaluated": 40,
            "probability_rows_count": 40,
            "probability_output_rate": 1.0,
            "top_probability_home_count": 20,
            "top_probability_draw_count": 5,
            "top_probability_away_count": 15,
            "top_probability_hit_count": 12,
            "top_probability_miss_count": 28,
            "top_probability_hit_rate": 0.3,
            "insufficient_source_data_count": 0,
            "decision_count": 40,
            "no_decision_count": 0,
            "data_blocked_count": 0,
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        },
    )

    assert run_v27_prematch_evaluation.main(["--input", "unused.csv"]) == 0
    output = _parse_console(capsys.readouterr().out)
    validation = validate_probability_evaluation_output(output)

    assert validation["schema_validation_status"] == "READY"
    assert all(field in output for field in REQUIRED_PROBABILITY_EVALUATION_FIELDS)
    assert not any(field in output for field in FORBIDDEN_PROBABILITY_EVALUATION_FIELDS)
    assert output["automatic_betting_enabled"] == "false"
    assert output["staking_logic_enabled"] == "false"
    assert output["roi_logic_enabled"] == "false"


def _parse_console(text: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
