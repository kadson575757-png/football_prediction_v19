# -*- coding: utf-8 -*-
"""Run the full one-command match analysis preview pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.real_match_analysis_command_preview import RealMatchAnalysisCommandConfig, RealMatchAnalysisCommandRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["cross-provider-match-key", "understat-provider-match-id", "fbref-provider-match-id", "home-team", "away-team", "match-date", "competition", "season"]:
        parser.add_argument(f"--{arg}", default=None)
    parser.add_argument("--real-match-intake", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "real_match_analysis_command"))
    parser.add_argument("--workbook-filename", default="match_analysis_preview_workbook.xlsx")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_match_analysis_preview(**kwargs: object) -> dict[str, object]:
    real_match_intake = kwargs.pop("real_match_intake", None)
    if real_match_intake:
        from scripts.build_real_match_analysis_runner_preview import build_real_match_analysis_runner_preview

        return build_real_match_analysis_runner_preview(real_match_intake_path=real_match_intake, base_dir=kwargs.get("base_dir", ROOT))
    result = RealMatchAnalysisCommandRunner(RealMatchAnalysisCommandConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_match_analysis_preview(
        cross_provider_match_key=args.cross_provider_match_key,
        understat_provider_match_id=args.understat_provider_match_id,
        fbref_provider_match_id=args.fbref_provider_match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        competition=args.competition,
        season=args.season,
        real_match_intake=args.real_match_intake,
        output_dir=args.output_dir,
        workbook_filename=args.workbook_filename,
        base_dir=args.base_dir,
    )
    for key in [
        "command_status", "match_context_bundle_status", "context_bridge_status",
        "real_match_analysis_runner_status",
        "real_match_input_pack_status", "real_match_intake_schema_status",
        "real_match_intake_validation_status", "manual_evidence_overlay_status",
        "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
        "odds_market_movement_input_status", "market_movement_diagnostic_status",
        "lineups_availability_input_status", "availability_diagnostic_status",
        "player_impact_rolling_form_input_status", "player_form_diagnostic_status",
        "tactical_set_piece_fatigue_input_status", "tactical_matchup_diagnostic_status",
        "human_24_block_report_status", "export_bundle_status", "excel_export_status",
        "home_team", "away_team", "match_date", "gates_evaluated", "gates_blocked",
        "gates_disabled", "sections_rendered", "required_sections_rendered",
        "exported_files_count", "sheets_written", "workbook_file_exists",
        "human_report_path", "excel_workbook_path", "artifact_index_path",
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "staking_logic_enabled", "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
