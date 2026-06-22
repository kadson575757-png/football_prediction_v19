# -*- coding: utf-8 -*-
"""Build deterministic Phase 28 player/form + 24-block preview."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.run_match_analysis_preview import run_match_analysis_preview  # noqa: E402


def build_player_form_diagnostic_24_block_preview_helper() -> dict[str, object]:
    summary = run_match_analysis_preview(cross_provider_match_key="u-bundesliga-2024-001", base_dir=ROOT)
    summary["match_analysis_runner_status"] = "MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    summary["recommendation"] = "PLAYER_FORM_DIAGNOSTIC_24_BLOCK_PREVIEW_READY" if summary.get("command_status") == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY" else "BUILD_PLAYER_FORM_DIAGNOSTIC_24_BLOCK_PREVIEW"
    return summary


def main() -> int:
    summary = build_player_form_diagnostic_24_block_preview_helper()
    for key in [
        "command_status", "odds_market_movement_input_status", "market_movement_diagnostic_status",
        "lineups_availability_input_status", "availability_diagnostic_status",
        "player_impact_rolling_form_input_status", "player_form_diagnostic_status",
        "match_analysis_runner_status", "v19_diagnostic_gate_matrix_status",
        "human_24_block_report_status", "export_bundle_status", "excel_export_status",
        "sheets_written", "workbook_file_exists", "sections_rendered",
        "required_sections_rendered", "gates_evaluated", "network_calls_enabled",
        "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
        "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
