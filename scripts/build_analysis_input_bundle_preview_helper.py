# -*- coding: utf-8 -*-
"""Build and audit the Phase 16.1 analysis input bundle preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_analysis_input_bundle_preview import run as run_audit  # noqa: E402
from build_analysis_input_bundle_preview import build_analysis_input_bundle_preview  # noqa: E402
from build_file_based_importer_dry_run_preview import build_file_based_importer_dry_run_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "input_bundle"))
    return parser


def run_workflow(output_dir: str | Path) -> dict[str, object]:
    importer = build_file_based_importer_dry_run_preview(output_dir=ROOT / "outputs" / "importer_preview", write_preview=True, base_dir=ROOT)
    summary = build_analysis_input_bundle_preview(
        input_path=importer.get("normalized_output_path") or None,
        output_dir=output_dir,
        write_preview=True,
        build_missing_importer_preview=True,
        base_dir=ROOT,
    )
    _table, _markdown, rec = run_audit(manifest=summary.get("bundle_manifest_path") or None, output_dir=ROOT / "outputs" / "diagnostics", base_dir=ROOT)
    return {**summary, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.output_dir)
    for key in ["analysis_input_bundle_status", "rows_input", "rows_ready", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation", "bundle_manifest_path"]:
        print(f"{key}={str(summary[key]).lower() if key.endswith('_enabled') else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

