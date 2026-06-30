# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2102_probability_output_schema import (  # noqa: E402
    FORBIDDEN_PROBABILITY_EVALUATION_FIELDS,
    FORBIDDEN_PROBABILITY_RUNNER_FIELDS,
    REQUIRED_PROBABILITY_EVALUATION_FIELDS,
    REQUIRED_PROBABILITY_RUNNER_FIELDS,
    validate_probability_evaluation_output,
    validate_probability_runner_output,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner-output-json", default="")
    parser.add_argument("--evaluation-output-json", default="")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)

    status = "READY"
    if args.runner_output_json:
        runner_validation = validate_probability_runner_output(_read_json(args.runner_output_json))
        if runner_validation["schema_validation_status"] != "READY":
            status = "FAILED"
    if args.evaluation_output_json:
        evaluation_validation = validate_probability_evaluation_output(_read_json(args.evaluation_output_json))
        if evaluation_validation["schema_validation_status"] != "READY":
            status = "FAILED"

    output = {
        "v2102_probability_output_schema_status": status,
        "runner_required_fields_count": len(REQUIRED_PROBABILITY_RUNNER_FIELDS),
        "runner_forbidden_fields_count": len(FORBIDDEN_PROBABILITY_RUNNER_FIELDS),
        "evaluation_required_fields_count": len(REQUIRED_PROBABILITY_EVALUATION_FIELDS),
        "evaluation_forbidden_fields_count": len(FORBIDDEN_PROBABILITY_EVALUATION_FIELDS),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    for key, value in output.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0 if status == "READY" else 1


def _read_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
