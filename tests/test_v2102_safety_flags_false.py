from scripts import validate_v2102_probability_output_schema
from football_prediction_v19.analysis.v2102_probability_output_schema import (
    REQUIRED_PROBABILITY_EVALUATION_FIELDS,
    REQUIRED_PROBABILITY_RUNNER_FIELDS,
    validate_probability_evaluation_output,
    validate_probability_runner_output,
)


def test_v2102_schema_cli_safety_flags_false(capsys):
    assert validate_v2102_probability_output_schema.main(["--emit-all"]) == 0
    output = capsys.readouterr().out

    assert "automatic_betting_enabled=false" in output
    assert "staking_logic_enabled=false" in output
    assert "roi_logic_enabled=false" in output


def test_v2102_schema_validators_require_safety_false():
    runner = {field: "value" for field in REQUIRED_PROBABILITY_RUNNER_FIELDS}
    runner.update({"automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False})
    evaluation = {field: 1 for field in REQUIRED_PROBABILITY_EVALUATION_FIELDS}
    evaluation.update({"probability_evaluation_status": "READY", "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False})

    assert validate_probability_runner_output(runner)["safety_flags_valid"] is True
    assert validate_probability_evaluation_output(evaluation)["safety_flags_valid"] is True
