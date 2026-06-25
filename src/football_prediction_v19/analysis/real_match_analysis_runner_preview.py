# -*- coding: utf-8 -*-
"""User-facing preview runner for manually supplied real match intake."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY = "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_VALIDATION_FAILED = "REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_VALIDATION_FAILED"
REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_OVERLAY_FAILED = "REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_OVERLAY_FAILED"
REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH = "REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH"
REAL_MATCH_ANALYSIS_RUNNER_NO_BETTING_OUTPUT_BY_DESIGN = "REAL_MATCH_ANALYSIS_RUNNER_NO_BETTING_OUTPUT_BY_DESIGN"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class RealMatchAnalysisRunnerConfig:
    real_match_intake_path: str | Path | None = None
    manual_evidence_completion_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/real_match_analysis_runner"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class RealMatchAnalysisRunnerResult:
    real_match_analysis_runner_status: str
    real_match_input_pack_status: str
    real_match_intake_validation_status: str
    manual_evidence_completion_status: str
    fields_completed_count: int
    remaining_missing_fields_count: int
    completed_evidence_groups: str
    manual_evidence_overlay_status: str
    odds_market_movement_input_status: str
    market_movement_diagnostic_status: str
    lineups_availability_input_status: str
    availability_diagnostic_status: str
    player_impact_rolling_form_input_status: str
    player_form_diagnostic_status: str
    tactical_set_piece_fatigue_input_status: str
    tactical_matchup_diagnostic_status: str
    v19_diagnostic_synthesis_status: str
    v19_diagnostic_gate_matrix_status: str
    human_24_block_report_status: str
    export_bundle_status: str
    excel_export_status: str
    sections_rendered: int
    required_sections_rendered: int
    sheets_written: int
    exported_files_count: int
    workbook_file_exists: bool
    home_team: str
    away_team: str
    match_date: str
    artifact_index_path: str
    manifest_path: str
    summary_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class RealMatchAnalysisRunner:
    def __init__(self, config: RealMatchAnalysisRunnerConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> RealMatchAnalysisRunnerResult:
        if not self.config.real_match_intake_path or _unsafe(self.config.real_match_intake_path):
            return self._blocked(REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH)
        from scripts.build_real_match_input_pack_preview import build_real_match_input_pack_preview

        pack = build_real_match_input_pack_preview(
            real_match_intake_path=self.config.real_match_intake_path,
            manual_evidence_completion_path=self.config.manual_evidence_completion_path,
            base_dir=self.base,
        )
        status = str(pack.get("real_match_input_pack_status", ""))
        if status == "REAL_MATCH_INPUT_PACK_BLOCKED_VALIDATION_FAILED":
            return self._blocked(REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_VALIDATION_FAILED, pack)
        if status == "REAL_MATCH_INPUT_PACK_BLOCKED_OVERLAY_FAILED":
            return self._blocked(REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_OVERLAY_FAILED, pack)
        if status != "REAL_MATCH_INPUT_PACK_PREVIEW_READY":
            return self._blocked(REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_VALIDATION_FAILED, pack)
        out = _safe_output(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        artifact_index = out / "real_match_analysis_runner_artifact_index.csv"
        manifest = out / "real_match_analysis_runner_manifest.csv"
        summary = out / "real_match_analysis_runner_summary.md"
        result = RealMatchAnalysisRunnerResult(
            REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY,
            str(pack.get("real_match_input_pack_status", "")),
            str(pack.get("real_match_intake_validation_status", "")),
            str(pack.get("manual_evidence_completion_status", "")),
            int(pack.get("fields_completed_count", 0) or 0),
            int(pack.get("remaining_missing_fields_count", 0) or 0),
            str(pack.get("completed_evidence_groups", "")),
            str(pack.get("manual_evidence_overlay_status", "")),
            str(pack.get("odds_market_movement_input_status", "")),
            str(pack.get("market_movement_diagnostic_status", "")),
            str(pack.get("lineups_availability_input_status", "")),
            str(pack.get("availability_diagnostic_status", "")),
            str(pack.get("player_impact_rolling_form_input_status", "")),
            str(pack.get("player_form_diagnostic_status", "")),
            str(pack.get("tactical_set_piece_fatigue_input_status", "")),
            str(pack.get("tactical_matchup_diagnostic_status", "")),
            "V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY",
            "V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY",
            str(pack.get("human_24_block_report_status", "")),
            str(pack.get("export_bundle_status", "")),
            str(pack.get("excel_export_status", "")),
            int(pack.get("sections_rendered", 0) or 0),
            int(pack.get("required_sections_rendered", 0) or 0),
            int(pack.get("sheets_written", 0) or 0),
            int(pack.get("exported_files_count", 0) or 0),
            (self.base / "outputs" / "analysis_preview" / "match_analysis_excel_export" / "match_analysis_preview_workbook.xlsx").exists(),
            str(pack.get("home_team", "")),
            str(pack.get("away_team", "")),
            str(pack.get("match_date", "")),
            str(artifact_index.resolve()),
            str(manifest.resolve()),
            str(summary.resolve()),
            REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([{"artifact_type": "real_match_input_pack", "artifact_path": pack.get("artifact_index_path", ""), "exists": Path(str(pack.get("artifact_index_path", ""))).exists()}]).to_csv(artifact_index, index=False)
        pd.DataFrame([result.__dict__]).to_csv(manifest, index=False)
        summary.write_text("\n".join([
            "# Real Match Analysis Runner Preview", "",
            f"- real_match_analysis_runner_status: {result.real_match_analysis_runner_status}",
            f"- manual_evidence_completion_status: {result.manual_evidence_completion_status}",
            f"- fields_completed_count: {result.fields_completed_count}",
            f"- remaining_missing_fields_count: {result.remaining_missing_fields_count}",
            f"- completed_evidence_groups: {result.completed_evidence_groups or 'none'}",
            f"- sheets_written: {result.sheets_written}",
            f"- exported_files_count: {result.exported_files_count}",
            "- Keine finale Wettempfehlung - Preview/Diagnostic only",
            "- no stake sizing, units, ROI, or SUPER_A output", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str, pack: dict[str, object] | None = None) -> RealMatchAnalysisRunnerResult:
        pack = pack or {}
        return RealMatchAnalysisRunnerResult(status, str(pack.get("real_match_input_pack_status", "")), str(pack.get("real_match_intake_validation_status", "")), str(pack.get("manual_evidence_completion_status", "")), int(pack.get("fields_completed_count", 0) or 0), int(pack.get("remaining_missing_fields_count", 0) or 0), str(pack.get("completed_evidence_groups", "")), str(pack.get("manual_evidence_overlay_status", "")), str(pack.get("odds_market_movement_input_status", "")), str(pack.get("market_movement_diagnostic_status", "")), str(pack.get("lineups_availability_input_status", "")), str(pack.get("availability_diagnostic_status", "")), str(pack.get("player_impact_rolling_form_input_status", "")), str(pack.get("player_form_diagnostic_status", "")), str(pack.get("tactical_set_piece_fatigue_input_status", "")), str(pack.get("tactical_matchup_diagnostic_status", "")), "", "", str(pack.get("human_24_block_report_status", "")), str(pack.get("export_bundle_status", "")), str(pack.get("excel_export_status", "")), 0, 0, 0, 0, False, str(pack.get("home_team", "")), str(pack.get("away_team", "")), str(pack.get("match_date", "")), "", "", "", status, False, False, False, False, False)


def _safe_output(output_dir: str | Path, base: Path) -> Path:
    out = Path(output_dir)
    return (base / out).resolve() if not out.is_absolute() else out.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)
