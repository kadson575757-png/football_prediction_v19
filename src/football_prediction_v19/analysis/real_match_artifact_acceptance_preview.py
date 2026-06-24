# -*- coding: utf-8 -*-
"""Acceptance audit for real match preview artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REAL_MATCH_ARTIFACT_ACCEPTANCE_PREVIEW_READY = "REAL_MATCH_ARTIFACT_ACCEPTANCE_PREVIEW_READY"
REAL_MATCH_ARTIFACT_ACCEPTANCE_BLOCKED_MISSING_ARTIFACTS = "REAL_MATCH_ARTIFACT_ACCEPTANCE_BLOCKED_MISSING_ARTIFACTS"
REAL_MATCH_ARTIFACT_ACCEPTANCE_BLOCKED_BETTING_OUTPUT_DETECTED = "REAL_MATCH_ARTIFACT_ACCEPTANCE_BLOCKED_BETTING_OUTPUT_DETECTED"
EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL = "EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL"


@dataclass(frozen=True)
class RealMatchArtifactAcceptanceConfig:
    base_dir: str | Path = "."
    output_dir: str | Path = "outputs/diagnostics"


@dataclass(frozen=True)
class RealMatchArtifactAcceptanceResult:
    real_match_artifact_acceptance_status: str
    artifacts_checked: int
    missing_artifacts_count: int
    sheets_written: int
    final_betting_output_detected: bool
    protected_logic_modified: bool
    output_path: str
    summary_path: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class RealMatchArtifactAcceptanceAuditor:
    def __init__(self, config: RealMatchArtifactAcceptanceConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> RealMatchArtifactAcceptanceResult:
        base = self.base / "outputs" / "analysis_preview"
        required = [
            base / "real_match_intake_schema" / "real_match_intake_template.csv",
            base / "filled_real_match_intake_pack" / "filled_real_match_intake.csv",
            base / "real_match_intake_validation" / "real_match_intake_validation.csv",
            base / "manual_evidence_overlay" / "manual_evidence_overlay.csv",
            base / "manual_evidence_overlay" / "odds_market_movement_input_overlay.csv",
            base / "manual_evidence_overlay" / "lineups_availability_input_overlay.csv",
            base / "manual_evidence_overlay" / "player_impact_rolling_form_input_overlay.csv",
            base / "manual_evidence_overlay" / "tactical_set_piece_fatigue_input_overlay.csv",
            base / "market_movement_diagnostic" / "market_movement_diagnostic.csv",
            base / "availability_diagnostic" / "availability_diagnostic.csv",
            base / "player_form_diagnostic" / "player_form_diagnostic.csv",
            base / "tactical_matchup_diagnostic" / "tactical_matchup_diagnostic.csv",
            base / "human_24_block_report" / "human_24_block_match_report_preview.md",
            base / "user_facing_real_match_report" / "user_facing_real_match_report.md",
            base / "match_analysis_export_bundle",
            base / "match_analysis_excel_export" / "match_analysis_preview_workbook.xlsx",
            base / "real_match_analysis_runner" / "real_match_analysis_runner_artifact_index.csv",
        ]
        missing = [p for p in required if not p.exists()]
        report_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in required if p.is_file() and p.suffix in {".md", ".csv"})
        forbidden = any(token in report_text.lower() for token in ["final betting tip", "stake size", "roi:", "super_a_tier promotion"])
        sheets = _sheets_written(base / "match_analysis_excel_export" / "match_analysis_excel_export_manifest.csv")
        status = REAL_MATCH_ARTIFACT_ACCEPTANCE_PREVIEW_READY
        if missing:
            status = REAL_MATCH_ARTIFACT_ACCEPTANCE_BLOCKED_MISSING_ARTIFACTS
        if forbidden:
            status = REAL_MATCH_ARTIFACT_ACCEPTANCE_BLOCKED_BETTING_OUTPUT_DETECTED
        out = _safe_output(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / "real_match_artifact_acceptance_preview_summary.csv"
        md_path = out / "real_match_artifact_acceptance_preview_summary.md"
        result = RealMatchArtifactAcceptanceResult(status, len(required), len(missing), sheets, forbidden, False, str(csv_path.resolve()), str(md_path.resolve()), False, False, False, False, False)
        pd.DataFrame([result.__dict__]).to_csv(csv_path, index=False)
        md_path.write_text("\n".join([
            "# Real Match Artifact Acceptance Preview", "",
            f"- real_match_artifact_acceptance_status: {status}",
            f"- artifacts_checked: {len(required)}",
            f"- missing_artifacts_count: {len(missing)}",
            f"- sheets_written: {sheets}",
            "- diagnostic only; no production prediction or betting output", "",
        ]), encoding="utf-8")
        return result


def _sheets_written(path: Path) -> int:
    if not path.exists():
        return 0
    frame = pd.read_csv(path)
    return int(frame.iloc[0].get("sheets_written", 0) or 0)


def _safe_output(output_dir: str | Path, base: Path) -> Path:
    out = Path(output_dir)
    return (base / out).resolve() if not out.is_absolute() else out.resolve()
