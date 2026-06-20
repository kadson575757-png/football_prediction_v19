# -*- coding: utf-8 -*-
"""Build Phase 17.1 manual human match input pack preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.manual_human_match_input import (  # noqa: E402
    ManualHumanMatchInputConfig,
    ManualHumanMatchInputTemplateBuilder,
    ManualHumanMatchInputValidator,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "manual_input"))
    parser.add_argument("--write-template", action="store_true")
    parser.add_argument("--write-example", action="store_true")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_manual_human_match_input_pack_preview(*, output_dir: str | Path, base_dir: str | Path = ROOT) -> dict[str, object]:
    builder = ManualHumanMatchInputTemplateBuilder(ManualHumanMatchInputConfig(output_dir=output_dir, base_dir=base_dir))
    written = builder.write()
    validator = ManualHumanMatchInputValidator(ManualHumanMatchInputConfig(input_path=written["example_path"], output_dir=output_dir, base_dir=base_dir))
    result, _frame = validator.validate()
    validator.write_outputs(result)
    return {**written, **result.__dict__}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_manual_human_match_input_pack_preview(output_dir=args.output_dir, base_dir=args.base_dir)
    for key in ["template_status", "example_status", "validation_status", "rows_input", "rows_valid", "rows_invalid", "required_columns_present", "optional_columns_present", "extra_columns_count", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if isinstance(summary[key], bool) else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

