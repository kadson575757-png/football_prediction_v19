# -*- coding: utf-8 -*-
"""Audit Phase 29 tactical matchup diagnostic integration."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.build_tactical_matchup_diagnostic_24_block_preview_helper import build_tactical_matchup_diagnostic_24_block_preview_helper  # noqa: E402

READY = "TACTICAL_MATCHUP_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
FIX = "FIX_TACTICAL_MATCHUP_DIAGNOSTIC_24_BLOCK_PREVIEW"


def audit_tactical_matchup_diagnostic_24_block_preview() -> dict[str, object]:
    summary = build_tactical_matchup_diagnostic_24_block_preview_helper()
    base = ROOT / "outputs" / "analysis_preview"
    diagnostics = ROOT / "outputs" / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    report = base / "human_24_block_report" / "human_24_block_match_report_preview.md"
    bundle = base / "match_analysis_export_bundle"
    workbook = Path(str(summary.get("excel_workbook_path", "")))
    report_text = report.read_text(encoding="utf-8") if report.exists() else ""
    checks = {
        "tactical_input_exists": (base / "tactical_set_piece_fatigue_input" / "tactical_set_piece_fatigue_input.csv").exists(),
        "tactical_diag_exists": (base / "tactical_matchup_diagnostic" / "tactical_matchup_diagnostic.csv").exists(),
        "bundle_tactical_input_review_exists": (bundle / "tactical_set_piece_fatigue_input_review.csv").exists(),
        "bundle_tactical_diag_review_exists": (bundle / "tactical_matchup_diagnostic_review.csv").exists(),
        "report_mentions_tactical": "Tactical diagnostic status" in report_text,
        "sheets_written_ge_16": int(summary.get("sheets_written", 0) or 0) >= 16,
        "workbook_file_exists": workbook.exists(),
        "sections_rendered_24": int(summary.get("sections_rendered", 0) or 0) == 24,
        "required_sections_rendered_24": int(summary.get("required_sections_rendered", 0) or 0) == 24,
        "gates_evaluated_ge_19": int(summary.get("gates_evaluated", 0) or 0) >= 19,
        "runtime_flags_disabled": not any(bool(summary.get(k, False)) for k in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]),
    }
    recommendation = READY if all(checks.values()) else FIX
    row = {**checks, "recommendation": recommendation}
    csv_path = diagnostics / "tactical_matchup_diagnostic_24_block_preview_summary.csv"
    md_path = diagnostics / "tactical_matchup_diagnostic_24_block_preview_summary.md"
    pd.DataFrame([row]).to_csv(csv_path, index=False)
    md_path.write_text("\n".join([
        "# Tactical Matchup Diagnostic 24-Block Preview Audit", "",
        f"- recommendation: {recommendation}",
        f"- sheets_written: {summary.get('sheets_written', 0)}",
        f"- report_mentions_tactical: {str(checks['report_mentions_tactical']).lower()}",
        "- Phase 29 is diagnostic only. No tier, probability, recommended-market, betting output, position sizing, or financial return tracking logic was changed.", "",
    ]), encoding="utf-8")
    return row


def main() -> int:
    result = audit_tactical_matchup_diagnostic_24_block_preview()
    print(result["recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
