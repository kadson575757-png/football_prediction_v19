# -*- coding: utf-8 -*-
"""Build v1.9 diagnostic synthesis plus integrated 24-block report preview."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_v19_diagnostic_24_block_report_preview import run as run_audit  # noqa: E402
from build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview  # noqa: E402
from build_human_24_block_report_preview import build_human_24_block_report_preview  # noqa: E402
from build_match_analysis_runner_preview import build_match_analysis_runner_preview  # noqa: E402
from build_v19_diagnostic_synthesis_preview import build_v19_diagnostic_synthesis_preview  # noqa: E402


READY = "V19_DIAGNOSTIC_24_BLOCK_REPORT_PREVIEW_READY"


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    key = "u-bundesliga-2024-001"
    runner = build_match_analysis_runner_preview(
        cross_provider_match_key=key,
        output_dir=base / "outputs" / "analysis_preview" / "match_analysis_runner",
        base_dir=base,
    )
    bridge = build_context_bundle_human_input_bridge_preview(
        cross_provider_match_key=key,
        output_dir=base / "outputs" / "analysis_preview" / "context_bundle_human_input",
        base_dir=base,
    )
    diagnostic = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=bridge["human_input_output_path"],
        cross_provider_match_key=key,
        output_dir=base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=base,
        build_missing=False,
    )
    report = build_human_24_block_report_preview(
        context_human_input_path=bridge["human_input_output_path"],
        v19_diagnostic_synthesis_path=diagnostic["output_path"],
        output_dir=base / "outputs" / "analysis_preview" / "human_24_block_report",
        base_dir=base,
        build_missing=False,
    )
    _table, _markdown, audit_rec = run_audit(
        diagnostic_manifest=diagnostic["manifest_path"],
        report_manifest=report["manifest_path"],
        output_dir=base / "outputs" / "diagnostics",
        base_dir=base,
    )
    return {
        **runner,
        "v19_diagnostic_synthesis_status": diagnostic["v19_diagnostic_synthesis_status"],
        "human_24_block_report_status": report["human_24_block_report_status"],
        "sections_rendered": report["sections_rendered"],
        "required_sections_rendered": report["required_sections_rendered"],
        "rows_diagnosed": diagnostic["rows_diagnosed"],
        "rows_reported": report["rows_reported"],
        "report_output_path": report["report_output_path"],
        "diagnostic_output_path": diagnostic["output_path"],
        "diagnostic_manifest_path": diagnostic["manifest_path"],
        "report_manifest_path": report["manifest_path"],
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "audit_recommendation": audit_rec,
        "recommendation": READY if audit_rec == READY else audit_rec,
    }


def main() -> int:
    summary = run_workflow(ROOT)
    for key in [
        "match_analysis_runner_status", "v19_diagnostic_synthesis_status",
        "human_24_block_report_status", "sections_rendered", "required_sections_rendered",
        "rows_diagnosed", "rows_reported", "report_output_path", "diagnostic_output_path", "network_calls_enabled",
        "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
        "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
