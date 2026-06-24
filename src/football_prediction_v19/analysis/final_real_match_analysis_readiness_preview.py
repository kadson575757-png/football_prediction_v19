# -*- coding: utf-8 -*-
"""Final readiness audit for the real match analysis preview workflow."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

FINAL_REAL_MATCH_ANALYSIS_READINESS_PREVIEW_READY = "FINAL_REAL_MATCH_ANALYSIS_READINESS_PREVIEW_READY"
FINAL_REAL_MATCH_ANALYSIS_READINESS_BLOCKED_FIX_REQUIRED = "FINAL_REAL_MATCH_ANALYSIS_READINESS_BLOCKED_FIX_REQUIRED"
FINAL_REAL_MATCH_ANALYSIS_READINESS_BLOCKED_BETTING_OUTPUT_DETECTED = "FINAL_REAL_MATCH_ANALYSIS_READINESS_BLOCKED_BETTING_OUTPUT_DETECTED"


@dataclass(frozen=True)
class FinalRealMatchAnalysisReadinessConfig:
    output_dir: str | Path = "outputs/diagnostics"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class FinalRealMatchAnalysisReadinessResult:
    final_real_match_analysis_readiness_status: str
    filled_real_match_intake_pack_status: str
    real_match_analysis_runner_status: str
    user_facing_real_match_report_status: str
    real_match_artifact_acceptance_status: str
    real_match_input_pack_status: str
    real_match_intake_validation_status: str
    manual_evidence_overlay_status: str
    market_movement_diagnostic_status: str
    availability_diagnostic_status: str
    player_form_diagnostic_status: str
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
    final_betting_output_detected: bool
    output_path: str
    summary_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class FinalRealMatchAnalysisReadinessAuditor:
    def __init__(self, config: FinalRealMatchAnalysisReadinessConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> FinalRealMatchAnalysisReadinessResult:
        from scripts.audit_real_match_artifact_acceptance_preview import audit_real_match_artifact_acceptance_preview
        from scripts.build_filled_real_match_intake_pack_preview import build_filled_real_match_intake_pack_preview
        from scripts.build_real_match_analysis_runner_preview import build_real_match_analysis_runner_preview
        from scripts.build_user_facing_real_match_report_preview import build_user_facing_real_match_report_preview

        filled = build_filled_real_match_intake_pack_preview(base_dir=self.base)
        runner = build_real_match_analysis_runner_preview(real_match_intake_path=filled.get("filled_intake_path"), base_dir=self.base)
        user_report = build_user_facing_real_match_report_preview(base_dir=self.base)
        acceptance = audit_real_match_artifact_acceptance_preview(base_dir=self.base)
        betting = bool(acceptance.get("final_betting_output_detected", False))
        ready = (
            runner.get("real_match_analysis_runner_status") == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
            and user_report.get("user_facing_real_match_report_status") == "USER_FACING_REAL_MATCH_REPORT_PREVIEW_READY"
            and acceptance.get("real_match_artifact_acceptance_status") == "REAL_MATCH_ARTIFACT_ACCEPTANCE_PREVIEW_READY"
            and not betting
        )
        status = FINAL_REAL_MATCH_ANALYSIS_READINESS_PREVIEW_READY if ready else FINAL_REAL_MATCH_ANALYSIS_READINESS_BLOCKED_FIX_REQUIRED
        if betting:
            status = FINAL_REAL_MATCH_ANALYSIS_READINESS_BLOCKED_BETTING_OUTPUT_DETECTED
        out = _safe_output(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / "final_real_match_analysis_readiness_preview_summary.csv"
        md_path = out / "final_real_match_analysis_readiness_preview_summary.md"
        result = FinalRealMatchAnalysisReadinessResult(
            status,
            str(filled.get("filled_real_match_intake_pack_status", "")),
            str(runner.get("real_match_analysis_runner_status", "")),
            str(user_report.get("user_facing_real_match_report_status", "")),
            str(acceptance.get("real_match_artifact_acceptance_status", "")),
            str(runner.get("real_match_input_pack_status", "")),
            str(runner.get("real_match_intake_validation_status", "")),
            str(runner.get("manual_evidence_overlay_status", "")),
            str(runner.get("market_movement_diagnostic_status", "")),
            str(runner.get("availability_diagnostic_status", "")),
            str(runner.get("player_form_diagnostic_status", "")),
            str(runner.get("tactical_matchup_diagnostic_status", "")),
            str(runner.get("v19_diagnostic_synthesis_status", "")),
            str(runner.get("v19_diagnostic_gate_matrix_status", "")),
            str(runner.get("human_24_block_report_status", "")),
            str(runner.get("export_bundle_status", "")),
            str(runner.get("excel_export_status", "")),
            int(runner.get("sections_rendered", 0) or 0),
            int(runner.get("required_sections_rendered", 0) or 0),
            int(runner.get("sheets_written", 0) or 0),
            int(runner.get("exported_files_count", 0) or 0),
            betting,
            str(csv_path.resolve()),
            str(md_path.resolve()),
            status,
            False, False, False, False, False,
        )
        pd.DataFrame([result.__dict__]).to_csv(csv_path, index=False)
        md_path.write_text("\n".join([
            "# Final Real Match Analysis Readiness Preview", "",
            f"- final_real_match_analysis_readiness_status: {status}",
            f"- real_match_analysis_runner_status: {result.real_match_analysis_runner_status}",
            f"- real_match_artifact_acceptance_status: {result.real_match_artifact_acceptance_status}",
            "- First real manual analysis preview is ready when this status is READY.",
            "- No final betting tips, stake sizing, units, ROI, or SUPER_A output.", "",
        ]), encoding="utf-8")
        return result


def _safe_output(output_dir: str | Path, base: Path) -> Path:
    out = Path(output_dir)
    return (base / out).resolve() if not out.is_absolute() else out.resolve()
