# -*- coding: utf-8 -*-
"""Validate a local manual human match input CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.manual_human_match_input import ManualHumanMatchInputConfig, ManualHumanMatchInputValidator  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "manual_input"))
    parser.add_argument("--allow-extra-columns", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def validate_manual_human_match_input(*, input_path: str | Path, output_dir: str | Path, allow_extra_columns: bool = True, base_dir: str | Path = ROOT) -> dict[str, object]:
    validator = ManualHumanMatchInputValidator(ManualHumanMatchInputConfig(input_path=input_path, output_dir=output_dir, allow_extra_columns=allow_extra_columns, base_dir=base_dir))
    result, _frame = validator.validate()
    paths = validator.write_outputs(result)
    return {**result.__dict__, **paths}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = validate_manual_human_match_input(input_path=args.input, output_dir=args.output_dir, allow_extra_columns=args.allow_extra_columns, base_dir=args.base_dir)
    for key in ["validation_status", "rows_input", "rows_valid", "rows_invalid", "required_columns_present", "missing_required_columns", "empty_required_values", "duplicate_match_ids", "extra_columns_count", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if isinstance(summary[key], bool) else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

