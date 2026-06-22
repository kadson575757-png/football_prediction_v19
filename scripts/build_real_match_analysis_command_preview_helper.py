# -*- coding: utf-8 -*-
"""Build deterministic one-command real match analysis preview."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_real_match_analysis_command_preview import run as run_audit  # noqa: E402
from run_match_analysis_preview import run_match_analysis_preview  # noqa: E402


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    summary = run_match_analysis_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=base / "outputs" / "analysis_preview" / "real_match_analysis_command",
        base_dir=base,
    )
    _table, _markdown, rec = run_audit(
        command_manifest=summary.get("manifest_path"),
        output_dir=base / "outputs" / "diagnostics",
        base_dir=base,
    )
    return {**summary, "audit_recommendation": rec}


def main() -> int:
    summary = run_workflow(ROOT)
    for key in [
        "command_status", "match_context_bundle_status", "context_bridge_status",
        "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
        "human_24_block_report_status", "export_bundle_status", "excel_export_status",
        "gates_evaluated", "sections_rendered", "required_sections_rendered",
        "exported_files_count", "sheets_written", "workbook_file_exists",
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "staking_logic_enabled", "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
