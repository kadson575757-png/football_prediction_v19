from football_prediction_v19.analysis.v2102_probability_output_schema import (
    REQUIRED_PROBABILITY_EVALUATION_FIELDS,
    REQUIRED_PROBABILITY_RUNNER_FIELDS,
    validate_probability_evaluation_output,
    validate_probability_runner_output,
)


def test_v2102_runner_validator_detects_missing_required_field():
    output = _runner_output()
    output.pop("probability_summary")

    validation = validate_probability_runner_output(output)

    assert validation["schema_validation_status"] == "FAILED"
    assert validation["missing_required_fields"] == ["probability_summary"]


def test_v2102_runner_validator_detects_forbidden_field():
    output = _runner_output()
    output["decision_class"] = "PROBABILITY_ONLY"

    validation = validate_probability_runner_output(output)

    assert validation["schema_validation_status"] == "FAILED"
    assert validation["forbidden_fields_present"] == ["decision_class"]


def test_v2102_runner_validator_detects_forbidden_text_pattern():
    output = _runner_output()
    output["probability_summary"] = "This row contains NO_DECISION legacy text."

    validation = validate_probability_runner_output(output)

    assert validation["schema_validation_status"] == "FAILED"
    assert "NO_DECISION" in validation["forbidden_text_patterns_present"]


def test_v2102_evaluation_validator_detects_forbidden_field():
    output = _evaluation_output()
    output["decision_count"] = 1

    validation = validate_probability_evaluation_output(output)

    assert validation["schema_validation_status"] == "FAILED"
    assert validation["forbidden_fields_present"] == ["decision_count"]


def test_v2102_validators_check_safety_flags_false():
    runner = _runner_output()
    runner["roi_logic_enabled"] = True
    evaluation = _evaluation_output()
    evaluation["staking_logic_enabled"] = True

    assert validate_probability_runner_output(runner)["safety_flags_valid"] is False
    assert validate_probability_evaluation_output(evaluation)["safety_flags_valid"] is False


def _runner_output() -> dict[str, object]:
    output = {field: "value" for field in REQUIRED_PROBABILITY_RUNNER_FIELDS}
    output.update(
        {
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
            "home_win_probability": 0.48,
            "draw_probability": 0.27,
            "away_win_probability": 0.25,
            "base_home_win_probability": 0.48,
            "base_draw_probability": 0.27,
            "base_away_probability": 0.25,
        }
    )
    return output


def _evaluation_output() -> dict[str, object]:
    output = {field: 1 for field in REQUIRED_PROBABILITY_EVALUATION_FIELDS}
    output.update(
        {
            "probability_evaluation_status": "READY",
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        }
    )
    return output
