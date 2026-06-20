# -*- coding: utf-8 -*-
"""Run the human match pipeline preview from a manual input CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_human_match_pipeline_preview import build_human_match_pipeline_preview  # noqa: E402
from validate_manual_human_match_input import validate_manual_human_match_input  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--match-id", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "human_match_pipeline"))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--validate-input", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_pipeline_from_manual_input(*, input_path: str | Path, match_id: str | None = None, output_dir: str | Path, write_preview: bool = True, validate_input: bool = True, base_dir: str | Path = ROOT) -> dict[str, object]:
    validation = validate_manual_human_match_input(input_path=input_path, output_dir=Path(base_dir) / "outputs" / "analysis_preview" / "manual_input", base_dir=base_dir) if validate_input else {"validation_status": "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY"}
    if validation["validation_status"] != "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY":
        return {**validation, "human_match_pipeline_status": "", "rows_reported": 0, "steps_failed": 0, "final_report_path": ""}
    pipeline = build_human_match_pipeline_preview(input_path=input_path, match_id=match_id, output_dir=output_dir, write_preview=write_preview, base_dir=base_dir)
    return {**validation, **pipeline}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_pipeline_from_manual_input(input_path=args.input, match_id=args.match_id, output_dir=args.output_dir, write_preview=True, validate_input=args.validate_input, base_dir=args.base_dir)
    for key in ["validation_status", "human_match_pipeline_status", "rows_reported", "steps_failed", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "final_report_path", "recommendation"]:
        print(f"{key}={str(summary.get(key, '')).lower() if isinstance(summary.get(key), bool) else summary.get(key, '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

