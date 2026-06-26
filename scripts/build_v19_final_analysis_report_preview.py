# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.v19_final_analysis_report_preview import (  # noqa: E402
    V19FinalAnalysisReportConfig,
    V19FinalAnalysisReportRenderer,
)


def build_v19_final_analysis_report_preview(**kwargs: object) -> dict[str, object]:
    result, _report = V19FinalAnalysisReportRenderer(V19FinalAnalysisReportConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-human-input-path", default=None)
    parser.add_argument("--v19-diagnostic-synthesis-path", default=None)
    parser.add_argument("--v19-diagnostic-gate-matrix-path", default=None)
    parser.add_argument("--market-movement-diagnostic-path", default=None)
    parser.add_argument("--availability-diagnostic-path", default=None)
    parser.add_argument("--player-form-diagnostic-path", default=None)
    parser.add_argument("--tactical-matchup-diagnostic-path", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_final_analysis_report"))
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    summary = build_v19_final_analysis_report_preview(
        context_human_input_path=args.context_human_input_path,
        v19_diagnostic_synthesis_path=args.v19_diagnostic_synthesis_path,
        v19_diagnostic_gate_matrix_path=args.v19_diagnostic_gate_matrix_path,
        market_movement_diagnostic_path=args.market_movement_diagnostic_path,
        availability_diagnostic_path=args.availability_diagnostic_path,
        player_form_diagnostic_path=args.player_form_diagnostic_path,
        tactical_matchup_diagnostic_path=args.tactical_matchup_diagnostic_path,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
