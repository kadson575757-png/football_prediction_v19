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
    parser.add_argument("--manual-evidence-completion", default=None)
    parser.add_argument("--emit-v19-final-analysis-report", action="store_true", default=False)
    parser.add_argument("--emit-v19-decision-report", action="store_true", default=False)
    parser.add_argument("--emit-v19-recommendation-preview", action="store_true", default=False)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "real_match_analysis_command"))
    parser.add_argument("--workbook-filename", default="match_analysis_preview_workbook.xlsx")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_match_analysis_preview(**kwargs: object) -> dict[str, object]:
    real_match_intake = kwargs.pop("real_match_intake", None)
    manual_evidence_completion = kwargs.pop("manual_evidence_completion", None)
    emit_v19_final_analysis_report = bool(kwargs.pop("emit_v19_final_analysis_report", False))
    emit_v19_decision_report = bool(kwargs.pop("emit_v19_decision_report", False))
    emit_v19_recommendation_preview = bool(kwargs.pop("emit_v19_recommendation_preview", False))
    if real_match_intake:
        from scripts.build_real_match_analysis_runner_preview import build_real_match_analysis_runner_preview

        summary = build_real_match_analysis_runner_preview(
            real_match_intake_path=real_match_intake,
            manual_evidence_completion_path=manual_evidence_completion,
            base_dir=kwargs.get("base_dir", ROOT),
        )
        if emit_v19_final_analysis_report and summary.get("real_match_analysis_runner_status") == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY":
            from scripts.build_v19_final_analysis_report_preview import build_v19_final_analysis_report_preview

            final_report = build_v19_final_analysis_report_preview(base_dir=kwargs.get("base_dir", ROOT))
            summary.update(final_report)
        if (emit_v19_decision_report or emit_v19_recommendation_preview) and summary.get("real_match_analysis_runner_status") == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY":
            _append_decision_preview(summary, kwargs.get("base_dir", ROOT), emit_v19_decision_report)
        return summary
    result = RealMatchAnalysisCommandRunner(RealMatchAnalysisCommandConfig(**kwargs)).run()
    summary = result.__dict__
    if emit_v19_final_analysis_report and summary.get("command_status") == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY":
        from scripts.build_v19_final_analysis_report_preview import build_v19_final_analysis_report_preview

        final_report = build_v19_final_analysis_report_preview(base_dir=kwargs.get("base_dir", ROOT))
        summary.update(final_report)
    if (emit_v19_decision_report or emit_v19_recommendation_preview) and summary.get("command_status") == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY":
        _append_decision_preview(summary, kwargs.get("base_dir", ROOT), emit_v19_decision_report)
    return summary


def _append_decision_preview(summary: dict[str, object], base_dir: object, emit_report: bool) -> None:
    from scripts.build_v19_decision_engine_preview import build_v19_decision_engine_preview

    engine = build_v19_decision_engine_preview(base_dir=base_dir)
    summary.update(engine)
    if emit_report:
        from scripts.build_v19_decision_report_preview import build_v19_decision_report_preview

        report = build_v19_decision_report_preview(base_dir=base_dir)
        summary.update(report)


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
        manual_evidence_completion=args.manual_evidence_completion,
        emit_v19_final_analysis_report=args.emit_v19_final_analysis_report,
        emit_v19_decision_report=args.emit_v19_decision_report,
        emit_v19_recommendation_preview=args.emit_v19_recommendation_preview,
        output_dir=args.output_dir,
        workbook_filename=args.workbook_filename,
        base_dir=args.base_dir,
    )
    for key in [
        "command_status", "match_context_bundle_status", "context_bridge_status",
        "real_match_analysis_runner_status",
        "real_match_input_pack_status", "real_match_intake_schema_status",
        "real_match_intake_validation_status", "manual_evidence_completion_status",
        "fields_completed_count", "remaining_missing_fields_count", "completed_evidence_groups",
        "manual_evidence_overlay_status",
        "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
        "odds_market_movement_input_status", "market_movement_diagnostic_status",
        "lineups_availability_input_status", "availability_diagnostic_status",
        "player_impact_rolling_form_input_status", "player_form_diagnostic_status",
        "tactical_set_piece_fatigue_input_status", "tactical_matchup_diagnostic_status",
        "human_24_block_report_status", "export_bundle_status", "excel_export_status",
        "v19_final_analysis_report_status", "report_output_path",
        "v19_decision_engine_preview_status", "v19_decision_report_status",
        "v19_decision_report_path", "recommendation_preview_enabled",
        "final_decision_preview", "evidence_readiness_score", "strongest_analyst_lean",
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
