# -*- coding: utf-8 -*-
"""Build and audit Phase 18.3 provider-to-human bundle preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_provider_to_human_analysis_bundle_preview import run as run_audit  # noqa: E402
from build_provider_to_human_analysis_bundle_preview import build_provider_to_human_analysis_bundle_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    summary = build_provider_to_human_analysis_bundle_preview(base_dir=base, output_dir=base / "outputs" / "analysis_preview" / "provider_to_human_bundle")
    _table, _markdown, rec = run_audit(manifest=summary.get("manifest_path") or None, output_dir=base / "outputs" / "diagnostics", base_dir=base)
    return {**summary, "provider_to_human_bundle_status": summary["bundle_status"], "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.base_dir)
    for key in [
        "provider_to_human_bundle_status", "provider_pull_status", "match_finder_status",
        "manual_input_bridge_status", "validation_status", "human_match_pipeline_status",
        "rows_reported", "steps_failed", "network_calls_enabled", "prediction_logic_enabled",
        "betting_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
