# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.build_real_match_input_pack_preview_helper import build_real_match_input_pack_preview_helper  # noqa: E402

READY = "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
FIX = "FIX_REAL_MATCH_INPUT_PACK_PREVIEW"


def audit_real_match_input_pack_preview() -> dict[str, object]:
    summary = build_real_match_input_pack_preview_helper()
    base = ROOT / "outputs" / "analysis_preview"
    diagnostics = ROOT / "outputs" / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    report = base / "human_24_block_report" / "human_24_block_match_report_preview.md"
    bundle = base / "match_analysis_export_bundle"
    workbook = base / "match_analysis_excel_export" / "match_analysis_preview_workbook.xlsx"
    report_text = report.read_text(encoding="utf-8") if report.exists() else ""
    checks = {
        "template_exists": (base / "real_match_intake_schema" / "real_match_intake_template.csv").exists(),
        "validation_exists": (base / "real_match_intake_validation" / "real_match_intake_validation.csv").exists(),
        "overlay_exists": (base / "manual_evidence_overlay" / "manual_evidence_overlay.csv").exists(),
        "overlay_split_files_exist": all((base / "manual_evidence_overlay" / name).exists() for name in [
            "odds_market_movement_input_overlay.csv", "lineups_availability_input_overlay.csv",
            "player_impact_rolling_form_input_overlay.csv", "tactical_set_piece_fatigue_input_overlay.csv",
        ]),
        "diagnostics_ready": all(str(summary.get(k, "")).endswith("PREVIEW_READY") for k in [
            "market_movement_diagnostic_status", "availability_diagnostic_status",
            "player_form_diagnostic_status", "tactical_matchup_diagnostic_status",
        ]),
        "report_exists_24_blocks": report.exists() and int(summary.get("sections_rendered", 0) or 0) == 24 and int(summary.get("required_sections_rendered", 0) or 0) == 24,
        "excel_ready": workbook.exists() and int(summary.get("sheets_written", 0) or 0) >= 16,
        "bundle_ready": bundle.exists() and int(summary.get("exported_files_count", 0) or 0) >= 14,
        "forbidden_text_absent": not any(token in report_text.lower() for token in ["stake size", "roi:", "super_a_tier promotion", "final betting tip"]),
        "runtime_flags_disabled": not any(bool(summary.get(k, False)) for k in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]),
    }
    recommendation = READY if all(checks.values()) else FIX
    row = {**checks, "recommendation": recommendation}
    pd.DataFrame([row]).to_csv(diagnostics / "real_match_input_pack_preview_summary.csv", index=False)
    (diagnostics / "real_match_input_pack_preview_summary.md").write_text("\n".join([
        "# Real Match Input Pack Preview Audit", "",
        f"- recommendation: {recommendation}",
        f"- sheets_written: {summary.get('sheets_written', 0)}",
        f"- exported_files_count: {summary.get('exported_files_count', 0)}",
        "- Phase 30 is diagnostic only. No model, probability, market, betting, staking, ROI, or SUPER_A_TIER logic was changed.", "",
    ]), encoding="utf-8")
    return row


def main() -> int:
    result = audit_real_match_input_pack_preview()
    print(result["recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
