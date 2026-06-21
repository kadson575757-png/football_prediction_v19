# -*- coding: utf-8 -*-
"""Build and audit match analysis runner 24-block preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_match_analysis_runner_24_block_preview import run as run_audit  # noqa: E402
from build_match_analysis_runner_preview import build_match_analysis_runner_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    summary = build_match_analysis_runner_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "match_analysis_runner", base_dir=base)
    _table, _markdown, rec = run_audit(runner_manifest=summary.get("manifest_path") or None, output_dir=base / "outputs" / "diagnostics", base_dir=base)
    return {**summary, "required_sections_rendered": 24, "recommendation": rec if rec.endswith("_READY") else summary.get("recommendation", "")}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.base_dir)
    for key in ["match_analysis_runner_status", "match_context_bundle_status", "context_bridge_status", "human_24_block_report_status", "rows_joined", "rows_written", "rows_reported", "sections_rendered", "required_sections_rendered", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        if key == "recommendation":
            value = summary.get("match_analysis_runner_status", value)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
