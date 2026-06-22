# -*- coding: utf-8 -*-
"""Audit Phase 28 player/form diagnostic integration."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.build_player_form_diagnostic_24_block_preview_helper import build_player_form_diagnostic_24_block_preview_helper  # noqa: E402

READY = "PLAYER_FORM_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
FIX = "FIX_PLAYER_FORM_DIAGNOSTIC_24_BLOCK_PREVIEW"


def audit_player_form_diagnostic_24_block_preview() -> dict[str, object]:
    summary = build_player_form_diagnostic_24_block_preview_helper()
    base = ROOT / "outputs" / "analysis_preview"
    diagnostics = ROOT / "outputs" / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    report = base / "human_24_block_report" / "human_24_block_match_report_preview.md"
    bundle = base / "match_analysis_export_bundle"
    workbook = Path(str(summary.get("excel_workbook_path", "")))
    report_text = report.read_text(encoding="utf-8") if report.exists() else ""
    checks = {
        "player_form_input_exists": (base / "player_impact_rolling_form_input" / "player_impact_rolling_form_input.csv").exists(),
        "player_form_diag_exists": (base / "player_form_diagnostic" / "player_form_diagnostic.csv").exists(),
        "bundle_player_form_input_review_exists": (bundle / "player_impact_rolling_form_input_review.csv").exists(),
        "bundle_player_form_diag_review_exists": (bundle / "player_form_diagnostic_review.csv").exists(),
        "report_mentions_player_form": "Player/form diagnostic status" in report_text,
        "sheets_written_ge_14": int(summary.get("sheets_written", 0) or 0) >= 14,
        "workbook_file_exists": workbook.exists(),
        "sections_rendered_24": int(summary.get("sections_rendered", 0) or 0) == 24,
        "required_sections_rendered_24": int(summary.get("required_sections_rendered", 0) or 0) == 24,
        "gates_evaluated_ge_19": int(summary.get("gates_evaluated", 0) or 0) >= 19,
        "runtime_flags_disabled": not any(bool(summary.get(k, False)) for k in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]),
    }
    recommendation = READY if all(checks.values()) else FIX
    row = {**checks, "recommendation": recommendation}
    csv_path = diagnostics / "player_form_diagnostic_24_block_preview_summary.csv"
    md_path = diagnostics / "player_form_diagnostic_24_block_preview_summary.md"
    pd.DataFrame([row]).to_csv(csv_path, index=False)
    md_path.write_text("\n".join([
        "# Player Form Diagnostic 24-Block Preview Audit", "",
        f"- recommendation: {recommendation}",
        f"- sheets_written: {summary.get('sheets_written', 0)}",
        f"- report_mentions_player_form: {str(checks['report_mentions_player_form']).lower()}",
        "- Phase 28 is diagnostic only. No tier, probability, recommended-market, betting output, position sizing, or financial return tracking logic was changed.", "",
    ]), encoding="utf-8")
    return row


def main() -> int:
    result = audit_player_form_diagnostic_24_block_preview()
    print(result["recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
