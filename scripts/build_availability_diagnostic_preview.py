# -*- coding: utf-8 -*-
"""Build preview-only availability diagnostic."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.availability_diagnostic_preview import AvailabilityDiagnosticConfig, AvailabilityDiagnosticRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cross-provider-match-key", default=None)
    parser.add_argument("--lineups-availability-input", default=None)
    parser.add_argument("--v19-diagnostic-gate-matrix", default=None)
    parser.add_argument("--v19-diagnostic-synthesis", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "availability_diagnostic"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_availability_diagnostic_preview(**kwargs: object) -> dict[str, object]:
    return AvailabilityDiagnosticRunner(AvailabilityDiagnosticConfig(**kwargs)).run().__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_availability_diagnostic_preview(
        cross_provider_match_key=args.cross_provider_match_key,
        lineups_availability_input_path=args.lineups_availability_input,
        v19_diagnostic_gate_matrix_path=args.v19_diagnostic_gate_matrix,
        v19_diagnostic_synthesis_path=args.v19_diagnostic_synthesis,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    for key in ["availability_diagnostic_status", "rows_diagnosed", "availability_evidence_status", "lineup_confirmation_gate_status", "injuries_suspensions_gate_status", "formation_availability_gate_status", "goalkeeper_availability_gate_status", "key_absence_gate_status", "no_bet_availability_safety_status", "missing_availability_fields_count", "output_path", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
