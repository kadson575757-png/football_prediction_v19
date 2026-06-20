# -*- coding: utf-8 -*-
"""Build and audit the Phase 17.1 manual human match input pack preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_manual_human_match_input_pack_preview import run as run_audit  # noqa: E402
from build_human_match_pipeline_from_manual_input_preview import build_pipeline_from_manual_input  # noqa: E402
from build_manual_human_match_input_pack_preview import build_manual_human_match_input_pack_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "manual_input"))
    return parser


def run_workflow(output_dir: str | Path) -> dict[str, object]:
    summary = build_manual_human_match_input_pack_preview(output_dir=output_dir, base_dir=ROOT)
    pipeline = build_pipeline_from_manual_input(
        input_path=summary["example_path"],
        output_dir=ROOT / "outputs" / "analysis_preview" / "human_match_pipeline",
        write_preview=True,
        base_dir=ROOT,
    )
    _table, _markdown, rec = run_audit(preview_dir=output_dir, output_dir=ROOT / "outputs" / "diagnostics", base_dir=ROOT)
    return {
        **summary,
        **pipeline,
        "manual_human_match_input_pack_status": rec,
        "recommendation": rec,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.output_dir)
    for key in [
        "manual_human_match_input_pack_status",
        "validation_status",
        "human_match_pipeline_status",
        "rows_valid",
        "rows_reported",
        "steps_failed",
        "network_calls_enabled",
        "prediction_logic_enabled",
        "betting_logic_enabled",
        "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
