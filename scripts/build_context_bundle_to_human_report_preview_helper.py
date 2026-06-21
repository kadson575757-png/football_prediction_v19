# -*- coding: utf-8 -*-
"""Build and audit context bundle to enriched human report preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_context_bundle_to_human_report_preview import run as run_audit  # noqa: E402
from build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview  # noqa: E402
from build_context_enriched_human_report_preview import build_context_enriched_human_report_preview  # noqa: E402
from build_match_context_bundle_preview import build_match_context_bundle_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    bundle = build_match_context_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "match_context_bundle", base_dir=base)
    bridge = build_context_bundle_human_input_bridge_preview(match_context_bundle_path=bundle.get("output_path"), cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=base, build_missing=False)
    report = build_context_enriched_human_report_preview(context_human_input_path=bridge.get("human_input_output_path"), output_dir=base / "outputs" / "analysis_preview" / "context_enriched_human_report", base_dir=base, build_missing=False)
    _table, _markdown, rec = run_audit(report_manifest=report.get("manifest_path") or None, bridge_manifest=bridge.get("manifest_path") or None, bundle_manifest=bundle.get("manifest_path") or None, output_dir=base / "outputs" / "diagnostics", base_dir=base)
    return {**bundle, **bridge, **report, "context_bundle_status": bundle.get("context_bundle_status", ""), "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.base_dir)
    for key in ["context_bundle_status", "context_bridge_status", "context_report_status", "rows_joined", "rows_written", "rows_reported", "sections_rendered", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
