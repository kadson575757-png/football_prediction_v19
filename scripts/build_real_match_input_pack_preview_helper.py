# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.build_real_match_input_pack_preview import build_real_match_input_pack_preview  # noqa: E402


def build_real_match_input_pack_preview_helper() -> dict[str, object]:
    return build_real_match_input_pack_preview(base_dir=ROOT)


def main() -> int:
    summary = build_real_match_input_pack_preview_helper()
    for key in [
        "real_match_input_pack_status", "real_match_intake_schema_status",
        "real_match_intake_validation_status", "manual_evidence_overlay_status",
        "command_status", "odds_market_movement_input_status",
        "market_movement_diagnostic_status", "lineups_availability_input_status",
        "availability_diagnostic_status", "player_impact_rolling_form_input_status",
        "player_form_diagnostic_status", "tactical_set_piece_fatigue_input_status",
        "tactical_matchup_diagnostic_status", "human_24_block_report_status",
        "export_bundle_status", "excel_export_status", "sheets_written",
        "exported_files_count", "sections_rendered", "required_sections_rendered",
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "staking_logic_enabled", "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
