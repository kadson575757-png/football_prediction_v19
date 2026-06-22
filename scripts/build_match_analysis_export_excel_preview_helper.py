# -*- coding: utf-8 -*-
"""Build match analysis export bundle and Excel preview workbook."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_match_analysis_export_excel_preview import run as run_audit  # noqa: E402
from build_match_analysis_excel_export_preview import build_match_analysis_excel_export_preview  # noqa: E402
from build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview  # noqa: E402
from build_match_analysis_runner_preview import build_match_analysis_runner_preview  # noqa: E402


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    key = "u-bundesliga-2024-001"
    runner = build_match_analysis_runner_preview(
        cross_provider_match_key=key,
        output_dir=base / "outputs" / "analysis_preview" / "match_analysis_runner",
        base_dir=base,
    )
    bundle = build_match_analysis_export_bundle_preview(
        cross_provider_match_key=key,
        output_dir=base / "outputs" / "analysis_preview" / "match_analysis_export_bundle",
        base_dir=base,
    )
    excel = build_match_analysis_excel_export_preview(
        export_bundle_dir=bundle.get("export_bundle_dir"),
        output_dir=base / "outputs" / "analysis_preview" / "match_analysis_excel_export",
        base_dir=base,
    )
    _table, _markdown, audit_rec = run_audit(
        export_bundle_manifest=bundle.get("manifest_path"),
        excel_manifest=excel.get("manifest_path"),
        output_dir=base / "outputs" / "diagnostics",
        base_dir=base,
    )
    return {
        **runner,
        "export_bundle_status": bundle.get("export_bundle_status", ""),
        "excel_export_status": excel.get("excel_export_status", ""),
        "exported_files_count": bundle.get("exported_files_count", 0),
        "sheets_written": excel.get("sheets_written", 0),
        "workbook_file_exists": excel.get("workbook_file_exists", False),
        "workbook_output_path": excel.get("workbook_output_path", ""),
        "sections_rendered": bundle.get("sections_rendered", 0),
        "required_sections_rendered": bundle.get("required_sections_rendered", 0),
        "gates_evaluated": bundle.get("gates_evaluated", 0),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "audit_recommendation": audit_rec,
        "recommendation": excel.get("recommendation", audit_rec),
    }


def main() -> int:
    summary = run_workflow(ROOT)
    for key in [
        "export_bundle_status", "excel_export_status", "match_analysis_runner_status",
        "v19_diagnostic_gate_matrix_status", "human_24_block_report_status",
        "exported_files_count", "sheets_written", "workbook_file_exists",
        "gates_evaluated", "sections_rendered", "required_sections_rendered",
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "staking_logic_enabled", "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
