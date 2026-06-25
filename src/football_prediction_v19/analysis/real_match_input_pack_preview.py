# -*- coding: utf-8 -*-
"""Preview-only real match input pack orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REAL_MATCH_INPUT_PACK_PREVIEW_READY = "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
REAL_MATCH_INPUT_PACK_BLOCKED_VALIDATION_FAILED = "REAL_MATCH_INPUT_PACK_BLOCKED_VALIDATION_FAILED"
REAL_MATCH_INPUT_PACK_BLOCKED_OVERLAY_FAILED = "REAL_MATCH_INPUT_PACK_BLOCKED_OVERLAY_FAILED"
REAL_MATCH_INPUT_PACK_NO_BETTING_OUTPUT_BY_DESIGN = "REAL_MATCH_INPUT_PACK_NO_BETTING_OUTPUT_BY_DESIGN"


@dataclass(frozen=True)
class RealMatchInputPackConfig:
    real_match_intake_path: str | Path | None = None
    manual_key_generation_enabled: bool = True
    output_dir: str | Path = "outputs/analysis_preview/real_match_input_pack"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class RealMatchInputPackResult:
    real_match_input_pack_status: str
    real_match_intake_schema_status: str
    real_match_intake_validation_status: str
    manual_evidence_overlay_status: str
    command_status: str
    odds_market_movement_input_status: str
    market_movement_diagnostic_status: str
    lineups_availability_input_status: str
    availability_diagnostic_status: str
    player_impact_rolling_form_input_status: str
    player_form_diagnostic_status: str
    tactical_set_piece_fatigue_input_status: str
    tactical_matchup_diagnostic_status: str
    human_24_block_report_status: str
    export_bundle_status: str
    excel_export_status: str
    sheets_written: int
    exported_files_count: int
    sections_rendered: int
    required_sections_rendered: int
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


class RealMatchInputPackBuilder:
    def __init__(self, config: RealMatchInputPackConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> RealMatchInputPackResult:
        from scripts.build_availability_diagnostic_preview import build_availability_diagnostic_preview
        from scripts.build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview
        from scripts.build_human_24_block_report_preview import build_human_24_block_report_preview
        from scripts.build_lineups_availability_input_preview import build_lineups_availability_input_preview
        from scripts.build_manual_evidence_overlay_preview import build_manual_evidence_overlay_preview
        from scripts.build_market_movement_diagnostic_preview import build_market_movement_diagnostic_preview
        from scripts.build_match_analysis_excel_export_preview import build_match_analysis_excel_export_preview
        from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview
        from scripts.build_odds_market_movement_input_preview import build_odds_market_movement_input_preview
        from scripts.build_player_form_diagnostic_preview import build_player_form_diagnostic_preview
        from scripts.build_player_impact_rolling_form_input_preview import build_player_impact_rolling_form_input_preview
        from scripts.build_real_match_intake_schema_preview import build_real_match_intake_schema_preview
        from scripts.build_tactical_matchup_diagnostic_preview import build_tactical_matchup_diagnostic_preview
        from scripts.build_tactical_set_piece_fatigue_input_preview import build_tactical_set_piece_fatigue_input_preview
        from scripts.build_v19_diagnostic_gate_matrix_preview import build_v19_diagnostic_gate_matrix_preview
        from scripts.build_v19_diagnostic_synthesis_preview import build_v19_diagnostic_synthesis_preview
        from scripts.validate_real_match_intake_preview import validate_real_match_intake_preview

        out = _safe_output(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        schema = build_real_match_intake_schema_preview(base_dir=self.base)
        intake_path = self.config.real_match_intake_path or schema.get("output_path")
        validation = validate_real_match_intake_preview(
            input_path=intake_path,
            manual_key_generation_enabled=self.config.manual_key_generation_enabled,
            base_dir=self.base,
        )
        if validation.get("real_match_intake_validation_status") != "REAL_MATCH_INTAKE_VALIDATION_READY":
            return self._blocked(REAL_MATCH_INPUT_PACK_BLOCKED_VALIDATION_FAILED, schema, validation)
        overlay = build_manual_evidence_overlay_preview(
            input_path=intake_path,
            manual_key_generation_enabled=self.config.manual_key_generation_enabled,
            output_dir=self.base / "outputs" / "analysis_preview" / "manual_evidence_overlay",
            base_dir=self.base,
        )
        if overlay.get("manual_evidence_overlay_status") != "MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY":
            return self._blocked(REAL_MATCH_INPUT_PACK_BLOCKED_OVERLAY_FAILED, schema, validation, overlay)

        key = _first_key(validation.get("output_path"))
        if self.config.real_match_intake_path:
            context = _build_manual_context_from_validation(
                validation_path=validation.get("output_path"),
                output_dir=self.base / "outputs" / "analysis_preview" / "context_bundle_human_input",
            )
        else:
            context = build_context_bundle_human_input_bridge_preview(
                cross_provider_match_key="u-bundesliga-2024-001",
                output_dir=self.base / "outputs" / "analysis_preview" / "context_bundle_human_input",
                base_dir=self.base,
            )
        synthesis = build_v19_diagnostic_synthesis_preview(context_human_input_path=context.get("human_input_output_path"), output_dir=self.base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis", base_dir=self.base)
        gate = build_v19_diagnostic_gate_matrix_preview(v19_diagnostic_synthesis_path=synthesis.get("output_path"), context_human_input_path=context.get("human_input_output_path"), output_dir=self.base / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix", base_dir=self.base)

        odds = build_odds_market_movement_input_preview(cross_provider_match_key=key, odds_input_path=overlay.get("odds_overlay_path"), output_dir=self.base / "outputs" / "analysis_preview" / "odds_market_movement_input", base_dir=self.base)
        market = build_market_movement_diagnostic_preview(cross_provider_match_key=key, odds_market_movement_input_path=odds.get("output_path"), v19_diagnostic_synthesis_path=synthesis.get("output_path"), v19_diagnostic_gate_matrix_path=gate.get("gate_matrix_output_path"), output_dir=self.base / "outputs" / "analysis_preview" / "market_movement_diagnostic", base_dir=self.base)
        lineups = build_lineups_availability_input_preview(cross_provider_match_key=key, availability_input_path=overlay.get("availability_overlay_path"), output_dir=self.base / "outputs" / "analysis_preview" / "lineups_availability_input", base_dir=self.base)
        availability = build_availability_diagnostic_preview(cross_provider_match_key=key, lineups_availability_input_path=lineups.get("output_path"), v19_diagnostic_synthesis_path=synthesis.get("output_path"), v19_diagnostic_gate_matrix_path=gate.get("gate_matrix_output_path"), output_dir=self.base / "outputs" / "analysis_preview" / "availability_diagnostic", base_dir=self.base)
        player_input = build_player_impact_rolling_form_input_preview(cross_provider_match_key=key, player_form_input_path=overlay.get("player_form_overlay_path"), output_dir=self.base / "outputs" / "analysis_preview" / "player_impact_rolling_form_input", base_dir=self.base)
        player = build_player_form_diagnostic_preview(cross_provider_match_key=key, player_impact_rolling_form_input_path=player_input.get("output_path"), v19_diagnostic_synthesis_path=synthesis.get("output_path"), v19_diagnostic_gate_matrix_path=gate.get("gate_matrix_output_path"), output_dir=self.base / "outputs" / "analysis_preview" / "player_form_diagnostic", base_dir=self.base)
        tactical_input = build_tactical_set_piece_fatigue_input_preview(cross_provider_match_key=key, tactical_input_path=overlay.get("tactical_overlay_path"), output_dir=self.base / "outputs" / "analysis_preview" / "tactical_set_piece_fatigue_input", base_dir=self.base)
        tactical = build_tactical_matchup_diagnostic_preview(cross_provider_match_key=key, tactical_set_piece_fatigue_input_path=tactical_input.get("output_path"), v19_diagnostic_synthesis_path=synthesis.get("output_path"), v19_diagnostic_gate_matrix_path=gate.get("gate_matrix_output_path"), output_dir=self.base / "outputs" / "analysis_preview" / "tactical_matchup_diagnostic", base_dir=self.base)
        report = build_human_24_block_report_preview(context_human_input_path=context.get("human_input_output_path"), v19_diagnostic_synthesis_path=synthesis.get("output_path"), v19_diagnostic_gate_matrix_path=gate.get("gate_matrix_output_path"), market_movement_diagnostic_path=market.get("output_path"), availability_diagnostic_path=availability.get("output_path"), player_form_diagnostic_path=player.get("output_path"), tactical_matchup_diagnostic_path=tactical.get("output_path"), output_dir=self.base / "outputs" / "analysis_preview" / "human_24_block_report", base_dir=self.base, build_missing=False)

        runner_manifest = _write_runner_manifest(self.base, context, synthesis, gate, odds, market, lineups, availability, player_input, player, tactical_input, tactical, report)
        bundle = build_match_analysis_export_bundle_preview(
            match_analysis_runner_manifest_path=runner_manifest,
            context_human_input_path=context.get("human_input_output_path"),
            v19_diagnostic_synthesis_path=synthesis.get("output_path"),
            v19_diagnostic_gate_matrix_path=gate.get("gate_matrix_output_path"),
            odds_market_movement_input_path=odds.get("output_path"),
            market_movement_diagnostic_path=market.get("output_path"),
            lineups_availability_input_path=lineups.get("output_path"),
            availability_diagnostic_path=availability.get("output_path"),
            player_impact_rolling_form_input_path=player_input.get("output_path"),
            player_form_diagnostic_path=player.get("output_path"),
            tactical_set_piece_fatigue_input_path=tactical_input.get("output_path"),
            tactical_matchup_diagnostic_path=tactical.get("output_path"),
            human_24_block_report_path=report.get("report_output_path"),
            output_dir=self.base / "outputs" / "analysis_preview" / "match_analysis_export_bundle",
            base_dir=self.base,
        )
        excel = build_match_analysis_excel_export_preview(export_bundle_dir=bundle.get("export_bundle_dir"), output_dir=self.base / "outputs" / "analysis_preview" / "match_analysis_excel_export", base_dir=self.base)
        result = RealMatchInputPackResult(
            REAL_MATCH_INPUT_PACK_PREVIEW_READY,
            str(schema.get("real_match_intake_schema_status", "")),
            str(validation.get("real_match_intake_validation_status", "")),
            str(overlay.get("manual_evidence_overlay_status", "")),
            "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY",
            str(odds.get("odds_market_movement_input_status", "")),
            str(market.get("market_movement_diagnostic_status", "")),
            str(lineups.get("lineups_availability_input_status", "")),
            str(availability.get("availability_diagnostic_status", "")),
            str(player_input.get("player_impact_rolling_form_input_status", "")),
            str(player.get("player_form_diagnostic_status", "")),
            str(tactical_input.get("tactical_set_piece_fatigue_input_status", "")),
            str(tactical.get("tactical_matchup_diagnostic_status", "")),
            str(report.get("human_24_block_report_status", "")),
            str(bundle.get("export_bundle_status", "")),
            str(excel.get("excel_export_status", "")),
            int(excel.get("sheets_written", 0) or 0),
            int(bundle.get("exported_files_count", 0) or 0),
            int(report.get("sections_rendered", 0) or 0),
            int(report.get("required_sections_rendered", 0) or 0),
            str(context.get("home_team", "")),
            str(context.get("away_team", "")),
            str(context.get("match_date", "")),
            str((out / "real_match_input_pack_artifact_index.csv").resolve()),
            str((out / "real_match_input_pack_manifest.csv").resolve()),
            str((out / "real_match_input_pack_summary.md").resolve()),
            REAL_MATCH_INPUT_PACK_PREVIEW_READY,
            False, False, False, False, False,
        )
        _write_outputs(out, result, [schema, validation, overlay, odds, market, lineups, availability, player_input, player, tactical_input, tactical, report, bundle, excel])
        return result

    def _blocked(self, status: str, schema: dict[str, object] | None = None, validation: dict[str, object] | None = None, overlay: dict[str, object] | None = None) -> RealMatchInputPackResult:
        return RealMatchInputPackResult(status, str((schema or {}).get("real_match_intake_schema_status", "")), str((validation or {}).get("real_match_intake_validation_status", "")), str((overlay or {}).get("manual_evidence_overlay_status", "")), "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, 0, 0, "", "", "", "", "", "", status, False, False, False, False, False)




def _build_manual_context_from_validation(validation_path: object, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(validation_path, low_memory=False).copy()

    if "analysis_input_id" not in frame.columns:
        frame["analysis_input_id"] = frame.get("cross_provider_match_key", "manual_real_match_input")
    frame["analysis_input_id"] = frame["analysis_input_id"].fillna("").astype(str)
    if "cross_provider_match_key" in frame.columns:
        frame.loc[frame["analysis_input_id"].str.strip().eq(""), "analysis_input_id"] = frame["cross_provider_match_key"]

    required_context_columns = [
        "analysis_input_id",
        "match_date",
        "competition",
        "season",
        "home_team",
        "away_team",
        "understat_provider_match_id",
        "fbref_provider_match_id",
        "cross_provider_match_key",
        "missing_required_fields",
        "missing_optional_fields",
    ]
    for column in required_context_columns:
        if column not in frame.columns:
            frame[column] = ""

    if "context_bundle_id" not in frame.columns:
        frame["context_bundle_id"] = "manual_real_match_context_preview"
    frame["context_bundle_id"] = frame["context_bundle_id"].fillna("").astype(str)
    if "cross_provider_match_key" in frame.columns:
        frame.loc[frame["context_bundle_id"].str.strip().eq(""), "context_bundle_id"] = frame["cross_provider_match_key"].astype(str)
    if "analysis_input_status" not in frame.columns:
        frame["analysis_input_status"] = "REAL_MATCH_MANUAL_CONTEXT_PREVIEW_ROW"
    if "context_data_quality_status" not in frame.columns:
        frame["context_data_quality_status"] = "MANUAL_REAL_MATCH_CONTEXT_FROM_INTAKE"
    if "understat_data_quality_status" not in frame.columns:
        frame["understat_data_quality_status"] = "MANUAL_OR_NOT_PROVIDED"
    if "fbref_data_quality_status" not in frame.columns:
        frame["fbref_data_quality_status"] = "MANUAL_OR_NOT_PROVIDED"
    if "recommendation" not in frame.columns:
        frame["recommendation"] = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY"
    if "notes" not in frame.columns:
        frame["notes"] = "Manual real-match intake context; no provider ID required."
    for flag in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        if flag not in frame.columns:
            frame[flag] = False

    manual_to_human_columns = {
        "home_team_xg_for": "home_xg",
        "away_team_xg_for": "away_xg",
        "home_team_xg_against": "home_xga",
        "away_team_xg_against": "away_xga",
    }
    for source_column, target_column in manual_to_human_columns.items():
        if target_column not in frame.columns:
            frame[target_column] = frame[source_column] if source_column in frame.columns else ""

    output_path = output_dir / "context_bundle_human_input.csv"
    frame.to_csv(output_path, index=False)
    return {
        "context_bridge_status": "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY",
        "human_input_output_path": str(output_path.resolve()),
        "rows_output": len(frame),
        "home_team": str(frame.iloc[0].get("home_team", "")) if not frame.empty else "",
        "away_team": str(frame.iloc[0].get("away_team", "")) if not frame.empty else "",
        "match_date": str(frame.iloc[0].get("match_date", "")) if not frame.empty else "",
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _safe_output(output_dir: str | Path, base: Path) -> Path:
    out = Path(output_dir)
    return (base / out).resolve() if not out.is_absolute() else out.resolve()


def _first_key(validation_path: object) -> str:
    frame = pd.read_csv(validation_path, low_memory=False)
    return str(frame.iloc[0].get("cross_provider_match_key", ""))


def _write_runner_manifest(base: Path, context: dict[str, object], synthesis: dict[str, object], gate: dict[str, object], odds: dict[str, object], market: dict[str, object], lineups: dict[str, object], availability: dict[str, object], player_input: dict[str, object], player: dict[str, object], tactical_input: dict[str, object], tactical: dict[str, object], report: dict[str, object]) -> Path:
    out = base / "outputs" / "analysis_preview" / "match_analysis_runner"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "match_analysis_runner_manifest.csv"
    pd.DataFrame([{
        "match_analysis_runner_status": "MATCH_ANALYSIS_RUNNER_PREVIEW_READY",
        "context_bridge_status": context.get("context_bridge_status", ""),
        "v19_diagnostic_synthesis_status": synthesis.get("v19_diagnostic_synthesis_status", ""),
        "v19_diagnostic_gate_matrix_status": gate.get("v19_diagnostic_gate_matrix_status", ""),
        "odds_market_movement_input_status": odds.get("odds_market_movement_input_status", ""),
        "market_movement_diagnostic_status": market.get("market_movement_diagnostic_status", ""),
        "lineups_availability_input_status": lineups.get("lineups_availability_input_status", ""),
        "availability_diagnostic_status": availability.get("availability_diagnostic_status", ""),
        "player_impact_rolling_form_input_status": player_input.get("player_impact_rolling_form_input_status", ""),
        "player_form_diagnostic_status": player.get("player_form_diagnostic_status", ""),
        "tactical_set_piece_fatigue_input_status": tactical_input.get("tactical_set_piece_fatigue_input_status", ""),
        "tactical_matchup_diagnostic_status": tactical.get("tactical_matchup_diagnostic_status", ""),
        "human_24_block_report_status": report.get("human_24_block_report_status", ""),
    }]).to_csv(path, index=False)
    return path


def _write_outputs(out: Path, result: RealMatchInputPackResult, artifacts: list[dict[str, object]]) -> None:
    rows = []
    for artifact in artifacts:
        for key in ["output_path", "gate_matrix_output_path", "human_input_output_path", "report_output_path", "export_bundle_dir", "workbook_output_path"]:
            value = artifact.get(key)
            if value:
                rows.append({"artifact_key": key, "artifact_path": value, "exists": Path(str(value)).exists()})
    pd.DataFrame(rows).to_csv(result.artifact_index_path, index=False)
    pd.DataFrame([result.__dict__]).to_csv(result.manifest_path, index=False)
    Path(result.summary_path).write_text("\n".join([
        "# Real Match Input Pack Preview", "",
        f"- real_match_input_pack_status: {result.real_match_input_pack_status}",
        f"- manual_evidence_overlay_status: {result.manual_evidence_overlay_status}",
        f"- sheets_written: {result.sheets_written}",
        f"- exported_files_count: {result.exported_files_count}",
        "- diagnostic preview only; no production prediction or betting output", "",
    ]), encoding="utf-8")
