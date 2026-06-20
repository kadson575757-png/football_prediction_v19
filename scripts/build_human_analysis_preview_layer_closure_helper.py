# -*- coding: utf-8 -*-
"""Build and audit Phase 16.6 human analysis preview layer closure."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_human_analysis_preview_layer_closure import run as run_closure  # noqa: E402
from build_human_match_pipeline_preview_helper import run_workflow as run_pipeline  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def run_workflow(output_dir: str | Path) -> dict[str, object]:
    run_pipeline(ROOT / "outputs" / "analysis_preview" / "human_match_pipeline")
    table, _markdown, rec = run_closure(output_dir=output_dir, base_dir=ROOT)
    row = table.iloc[0].to_dict()
    return {**row, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    row = run_workflow(args.output_dir)
    print(f"human_analysis_preview_layer_status={row['closure_status']}")
    print(f"pipeline_status={row['pipeline_status']}")
    print(f"human_report_status={row['human_report_status']}")
    print(f"rows_reported={row['rows_reported']}")
    print(f"steps_failed={row['steps_failed']}")
    print(f"network_calls_enabled={str(row['network_calls_enabled']).lower()}")
    print(f"prediction_logic_enabled={str(row['prediction_logic_enabled']).lower()}")
    print(f"betting_logic_enabled={str(row['betting_logic_enabled']).lower()}")
    print(f"recommendation={row['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

