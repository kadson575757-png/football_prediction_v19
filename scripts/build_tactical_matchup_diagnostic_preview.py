# -*- coding: utf-8 -*-
"""CLI wrapper for Phase 29 tactical matchup diagnostic preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.tactical_matchup_diagnostic_preview import (  # noqa: E402
    TacticalMatchupDiagnosticConfig,
    TacticalMatchupDiagnosticRunner,
)


def build_tactical_matchup_diagnostic_preview(**kwargs: object) -> dict[str, object]:
    result = TacticalMatchupDiagnosticRunner(TacticalMatchupDiagnosticConfig(**kwargs)).run()
    return {
        "tactical_matchup_diagnostic_status": result.tactical_matchup_diagnostic_status,
        "rows_diagnosed": result.rows_diagnosed,
        "tactical_evidence_status": result.tactical_evidence_status,
        "set_piece_xg_ratio_gate_status": result.set_piece_xg_ratio_gate_status,
        "tactical_matchup_score_gate_status": result.tactical_matchup_score_gate_status,
        "fatigue_modifier_gate_status": result.fatigue_modifier_gate_status,
        "xg_zone_correction_gate_status": result.xg_zone_correction_gate_status,
        "formation_matchup_gate_status": result.formation_matchup_gate_status,
        "transition_matchup_gate_status": result.transition_matchup_gate_status,
        "no_bet_tactical_safety_status": result.no_bet_tactical_safety_status,
        "missing_tactical_fields_count": result.missing_tactical_fields_count,
        "output_path": result.output_path,
        "summary_path": result.summary_path,
        "manifest_path": result.manifest_path,
        "recommendation": result.recommendation,
        "network_calls_enabled": result.network_calls_enabled,
        "prediction_logic_enabled": result.prediction_logic_enabled,
        "betting_logic_enabled": result.betting_logic_enabled,
        "staking_logic_enabled": result.staking_logic_enabled,
        "roi_logic_enabled": result.roi_logic_enabled,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cross-provider-match-key")
    parser.add_argument("--tactical-set-piece-fatigue-input-path")
    parser.add_argument("--v19-diagnostic-gate-matrix-path")
    parser.add_argument("--v19-diagnostic-synthesis-path")
    parser.add_argument("--output-dir", default="outputs/analysis_preview/tactical_matchup_diagnostic")
    args = parser.parse_args()
    summary = build_tactical_matchup_diagnostic_preview(
        cross_provider_match_key=args.cross_provider_match_key,
        tactical_set_piece_fatigue_input_path=args.tactical_set_piece_fatigue_input_path,
        v19_diagnostic_gate_matrix_path=args.v19_diagnostic_gate_matrix_path,
        v19_diagnostic_synthesis_path=args.v19_diagnostic_synthesis_path,
        output_dir=args.output_dir,
        base_dir=ROOT,
    )
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
