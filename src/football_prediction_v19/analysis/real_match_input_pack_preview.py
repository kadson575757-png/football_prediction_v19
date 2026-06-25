# -*- coding: utf-8 -*-
"""Preview-only real match input pack orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

REAL_MATCH_INPUT_PACK_PREVIEW_READY = "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
REAL_MATCH_INPUT_PACK_BLOCKED_VALIDATION_FAILED = "REAL_MATCH_INPUT_PACK_BLOCKED_VALIDATION_FAILED"
REAL_MATCH_INPUT_PACK_BLOCKED_OVERLAY_FAILED = "REAL_MATCH_INPUT_PACK_BLOCKED_OVERLAY_FAILED"
REAL_MATCH_INPUT_PACK_BLOCKED_COMPLETION_FAILED = "REAL_MATCH_INPUT_PACK_BLOCKED_COMPLETION_FAILED"
REAL_MATCH_INPUT_PACK_NO_BETTING_OUTPUT_BY_DESIGN = "REAL_MATCH_INPUT_PACK_NO_BETTING_OUTPUT_BY_DESIGN"
MANUAL_EVIDENCE_COMPLETION_NOT_PROVIDED = "MANUAL_EVIDENCE_COMPLETION_NOT_PROVIDED"
MANUAL_EVIDENCE_COMPLETION_APPLIED = "MANUAL_EVIDENCE_COMPLETION_APPLIED"
MANUAL_EVIDENCE_COMPLETION_BLOCKED_NO_MATCH = "MANUAL_EVIDENCE_COMPLETION_BLOCKED_NO_MATCH"
MANUAL_EVIDENCE_COMPLETION_BLOCKED_UNSAFE_PATH = "MANUAL_EVIDENCE_COMPLETION_BLOCKED_UNSAFE_PATH"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]

COMPLETION_GROUPS = {
    "Market/Odds": [
        "home_open_odds", "draw_open_odds", "away_open_odds", "home_current_odds",
        "draw_current_odds", "away_current_odds", "home_closing_odds", "draw_closing_odds",
        "away_closing_odds", "over_line", "over_open_odds", "under_open_odds",
        "over_current_odds", "under_current_odds", "dnb_home_odds", "dnb_away_odds",
        "handicap_line", "handicap_home_odds", "handicap_away_odds",
    ],
    "Match Stats/Control": [
        "home_possession", "away_possession", "home_shots", "away_shots",
        "home_shots_on_target", "away_shots_on_target", "home_tackles", "away_tackles",
        "home_interceptions", "away_interceptions", "home_blocks", "away_blocks",
        "home_clearances", "away_clearances", "home_progressive_passes",
        "away_progressive_passes", "home_progressive_carries", "away_progressive_carries",
        "home_pass_completion", "away_pass_completion", "home_pass_completion_pct",
        "away_pass_completion_pct",
    ],
    "Lineups/Availability": [
        "home_lineup_status", "away_lineup_status", "home_lineup_confirmed",
        "away_lineup_confirmed", "home_goalkeeper_status", "away_goalkeeper_status",
        "home_defensive_line_status", "away_defensive_line_status", "home_missing_players",
        "away_missing_players", "home_suspended_players", "away_suspended_players",
        "home_doubtful_players", "away_doubtful_players", "home_key_absence_count",
        "away_key_absence_count", "home_key_absences", "away_key_absences",
    ],
    "Player/Recent Form": [
        "home_big_chances_for", "away_big_chances_for", "home_big_chances",
        "away_big_chances", "home_big_chances_against", "away_big_chances_against",
        "home_recent_matches", "away_recent_matches", "home_recent_goals_for",
        "away_recent_goals_for", "home_recent_goals_against", "away_recent_goals_against",
        "home_recent_xg_for", "away_recent_xg_for", "home_recent_xg_against",
        "away_recent_xg_against", "home_recent_conversion_note",
        "away_recent_conversion_note", "home_conversion_signal", "away_conversion_signal",
    ],
    "Tactical/Fatigue": [
        "tactical_matchup_score", "home_tactical_profile", "away_tactical_profile",
        "formation_matchup_note", "pressing_matchup_note", "transition_matchup_note",
        "defensive_line_risk_note", "home_rest_days", "away_rest_days",
        "home_travel_fatigue_note", "away_travel_fatigue_note", "do_so_fatigue_modifier",
        "xg_zone_correction_flag", "xg_zone_correction_note",
    ],
    "H2H/Manual Notes": ["h2h_summary", "analyst_manual_note", "analyst_note"],
}

COMPLETION_ALIASES = {
    "home_lineup_status": "home_lineup_confirmed",
    "away_lineup_status": "away_lineup_confirmed",
    "home_key_absence_count": "home_key_absences",
    "away_key_absence_count": "away_key_absences",
    "home_big_chances_for": "home_big_chances",
    "away_big_chances_for": "away_big_chances",
    "home_recent_conversion_note": "home_conversion_signal",
    "away_recent_conversion_note": "away_conversion_signal",
    "home_pass_completion": "home_pass_completion_pct",
    "away_pass_completion": "away_pass_completion_pct",
    "analyst_manual_note": "analyst_note",
}


@dataclass(frozen=True)
class RealMatchInputPackConfig:
    real_match_intake_path: str | Path | None = None
    manual_evidence_completion_path: str | Path | None = None
    manual_key_generation_enabled: bool = True
    output_dir: str | Path = "outputs/analysis_preview/real_match_input_pack"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class RealMatchInputPackResult:
    real_match_input_pack_status: str
    real_match_intake_schema_status: str
    real_match_intake_validation_status: str
    manual_evidence_completion_status: str
    fields_completed_count: int
    remaining_missing_fields_count: int
    completed_evidence_groups: str
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
        completion = _apply_manual_evidence_completion(
            intake_path=intake_path,
            completion_path=self.config.manual_evidence_completion_path,
            output_dir=self.base / "outputs" / "analysis_preview" / "manual_evidence_completion",
            base=self.base,
        )
        if str(completion.get("manual_evidence_completion_status", "")).startswith("MANUAL_EVIDENCE_COMPLETION_BLOCKED"):
            return self._blocked(REAL_MATCH_INPUT_PACK_BLOCKED_COMPLETION_FAILED, schema, {"real_match_intake_validation_status": ""}, None, completion)
        intake_path = completion.get("completed_intake_path") or intake_path
        validation = validate_real_match_intake_preview(
            input_path=intake_path,
            manual_key_generation_enabled=self.config.manual_key_generation_enabled,
            base_dir=self.base,
        )
        if validation.get("real_match_intake_validation_status") != "REAL_MATCH_INTAKE_VALIDATION_READY":
            return self._blocked(REAL_MATCH_INPUT_PACK_BLOCKED_VALIDATION_FAILED, schema, validation, None, completion)
        overlay = build_manual_evidence_overlay_preview(
            input_path=intake_path,
            manual_key_generation_enabled=self.config.manual_key_generation_enabled,
            output_dir=self.base / "outputs" / "analysis_preview" / "manual_evidence_overlay",
            base_dir=self.base,
        )
        if overlay.get("manual_evidence_overlay_status") != "MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY":
            return self._blocked(REAL_MATCH_INPUT_PACK_BLOCKED_OVERLAY_FAILED, schema, validation, overlay, completion)

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
            str(completion.get("manual_evidence_completion_status", "")),
            int(completion.get("fields_completed_count", 0) or 0),
            int(completion.get("remaining_missing_fields_count", 0) or 0),
            str(completion.get("completed_evidence_groups", "")),
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
        _write_outputs(out, result, [schema, completion, validation, overlay, odds, market, lineups, availability, player_input, player, tactical_input, tactical, report, bundle, excel])
        return result

    def _blocked(self, status: str, schema: dict[str, object] | None = None, validation: dict[str, object] | None = None, overlay: dict[str, object] | None = None, completion: dict[str, object] | None = None) -> RealMatchInputPackResult:
        completion = completion or {}
        return RealMatchInputPackResult(
            real_match_input_pack_status=status,
            real_match_intake_schema_status=str((schema or {}).get("real_match_intake_schema_status", "")),
            real_match_intake_validation_status=str((validation or {}).get("real_match_intake_validation_status", "")),
            manual_evidence_completion_status=str(completion.get("manual_evidence_completion_status", "")),
            fields_completed_count=int(completion.get("fields_completed_count", 0) or 0),
            remaining_missing_fields_count=int(completion.get("remaining_missing_fields_count", 0) or 0),
            completed_evidence_groups=str(completion.get("completed_evidence_groups", "")),
            manual_evidence_overlay_status=str((overlay or {}).get("manual_evidence_overlay_status", "")),
            command_status="",
            odds_market_movement_input_status="",
            market_movement_diagnostic_status="",
            lineups_availability_input_status="",
            availability_diagnostic_status="",
            player_impact_rolling_form_input_status="",
            player_form_diagnostic_status="",
            tactical_set_piece_fatigue_input_status="",
            tactical_matchup_diagnostic_status="",
            human_24_block_report_status="",
            export_bundle_status="",
            excel_export_status="",
            sheets_written=0,
            exported_files_count=0,
            sections_rendered=0,
            required_sections_rendered=0,
            home_team="",
            away_team="",
            match_date="",
            artifact_index_path="",
            manifest_path="",
            summary_path="",
            recommendation=status,
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            staking_logic_enabled=False,
            roi_logic_enabled=False,
        )




def _apply_manual_evidence_completion(
    *,
    intake_path: object,
    completion_path: str | Path | None,
    output_dir: Path,
    base: Path,
) -> dict[str, object]:
    if completion_path is None or str(completion_path).strip() == "":
        return {
            "manual_evidence_completion_status": MANUAL_EVIDENCE_COMPLETION_NOT_PROVIDED,
            "fields_completed_count": 0,
            "remaining_missing_fields_count": 0,
            "completed_evidence_groups": "",
            "manual_evidence_completion_file_used": "no",
        }
    source = _resolve_path(completion_path, base)
    intake = _resolve_path(intake_path, base)
    if source is None or intake is None or _unsafe_completion_path(source) or _unsafe_completion_path(intake):
        return {
            "manual_evidence_completion_status": MANUAL_EVIDENCE_COMPLETION_BLOCKED_UNSAFE_PATH,
            "fields_completed_count": 0,
            "remaining_missing_fields_count": 0,
            "completed_evidence_groups": "",
            "manual_evidence_completion_file_used": "no",
        }
    try:
        intake_frame = pd.read_csv(intake, low_memory=False, keep_default_na=False)
        completion_frame = pd.read_csv(source, low_memory=False, keep_default_na=False)
    except (FileNotFoundError, EmptyDataError, OSError):
        return {
            "manual_evidence_completion_status": MANUAL_EVIDENCE_COMPLETION_BLOCKED_NO_MATCH,
            "fields_completed_count": 0,
            "remaining_missing_fields_count": 0,
            "completed_evidence_groups": "",
            "manual_evidence_completion_file_used": "no",
        }
    if intake_frame.empty or completion_frame.empty:
        return {
            "manual_evidence_completion_status": MANUAL_EVIDENCE_COMPLETION_BLOCKED_NO_MATCH,
            "fields_completed_count": 0,
            "remaining_missing_fields_count": 0,
            "completed_evidence_groups": "",
            "manual_evidence_completion_file_used": "no",
        }
    intake_row = intake_frame.iloc[0]
    match = _select_completion_row(intake_row, completion_frame)
    if match is None:
        return {
            "manual_evidence_completion_status": MANUAL_EVIDENCE_COMPLETION_BLOCKED_NO_MATCH,
            "fields_completed_count": 0,
            "remaining_missing_fields_count": _remaining_missing_fields(intake_frame.iloc[0]),
            "completed_evidence_groups": "",
            "manual_evidence_completion_file_used": "yes",
            "manual_evidence_completion_path": str(source),
        }

    changed_columns: list[str] = []
    for column in completion_frame.columns:
        value = match.get(column, "")
        if _blank(value):
            continue
        if column not in intake_frame.columns:
            intake_frame[column] = ""
        if _blank(intake_frame.at[0, column]):
            intake_frame.at[0, column] = value
            changed_columns.append(column)
        alias = COMPLETION_ALIASES.get(column)
        if alias:
            if alias not in intake_frame.columns:
                intake_frame[alias] = ""
            if _blank(intake_frame.at[0, alias]):
                intake_frame.at[0, alias] = value
                changed_columns.append(alias)

    groups = _completed_groups(changed_columns)
    intake_frame["manual_evidence_completion_status"] = MANUAL_EVIDENCE_COMPLETION_APPLIED
    intake_frame["manual_evidence_completion_file_used"] = "yes"
    intake_frame["manual_evidence_completion_path"] = str(source)
    intake_frame["fields_completed_count"] = len(changed_columns)
    intake_frame["remaining_missing_fields_count"] = _remaining_missing_fields(intake_frame.iloc[0])
    intake_frame["completed_evidence_groups"] = groups
    output_dir.mkdir(parents=True, exist_ok=True)
    completed_path = output_dir / "real_match_intake_completed.csv"
    summary_path = output_dir / "manual_evidence_completion_summary.md"
    manifest_path = output_dir / "manual_evidence_completion_manifest.csv"
    intake_frame.to_csv(completed_path, index=False)
    result = {
        "manual_evidence_completion_status": MANUAL_EVIDENCE_COMPLETION_APPLIED,
        "fields_completed_count": len(changed_columns),
        "remaining_missing_fields_count": _remaining_missing_fields(intake_frame.iloc[0]),
        "completed_evidence_groups": groups,
        "manual_evidence_completion_file_used": "yes",
        "manual_evidence_completion_path": str(source),
        "completed_intake_path": str(completed_path.resolve()),
        "output_path": str(completed_path.resolve()),
        "summary_path": str(summary_path.resolve()),
        "manifest_path": str(manifest_path.resolve()),
    }
    pd.DataFrame([result]).to_csv(manifest_path, index=False)
    summary_path.write_text("\n".join([
        "# Manual Evidence Completion Preview",
        "",
        f"- manual_evidence_completion_status: {MANUAL_EVIDENCE_COMPLETION_APPLIED}",
        f"- completion_file_used: yes",
        f"- fields_completed_count: {len(changed_columns)}",
        f"- remaining_missing_fields_count: {result['remaining_missing_fields_count']}",
        f"- completed_evidence_groups: {groups or 'none'}",
        "- only blank intake values were completed; source intake was not overwritten",
        "- diagnostic preview only; no production prediction or betting output",
        "",
    ]), encoding="utf-8")
    return result


def _select_completion_row(intake_row: pd.Series, completion_frame: pd.DataFrame) -> pd.Series | None:
    key = str(intake_row.get("cross_provider_match_key", "")).strip()
    if key and "cross_provider_match_key" in completion_frame.columns:
        narrowed = completion_frame[completion_frame["cross_provider_match_key"].astype(str).str.strip() == key]
        if len(narrowed) == 1:
            return narrowed.iloc[0]
        if len(narrowed) > 1:
            return None
    required = ["home_team", "away_team", "match_date"]
    if all(column in completion_frame.columns for column in required):
        mask = pd.Series([True] * len(completion_frame), index=completion_frame.index)
        for column in required:
            value = str(intake_row.get(column, "")).strip().lower()
            mask &= completion_frame[column].astype(str).str.strip().str.lower().eq(value)
        narrowed = completion_frame[mask]
        if len(narrowed) == 1:
            return narrowed.iloc[0]
    return None


def _completed_groups(columns: list[str]) -> str:
    groups: list[str] = []
    seen = set(columns)
    for group, group_columns in COMPLETION_GROUPS.items():
        if seen.intersection(group_columns):
            groups.append(group)
    return " | ".join(groups)


def _remaining_missing_fields(row: pd.Series) -> int:
    skip = {
        "match_date", "competition", "season", "home_team", "away_team",
        "cross_provider_match_key", "understat_provider_match_id", "fbref_provider_match_id",
        "missing_required_fields", "missing_optional_fields",
    }
    return len([column for column in row.index if column not in skip and _blank(row.get(column, ""))])


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


def _resolve_path(path: object, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(str(path))
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe_completion_path(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


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
        f"- manual_evidence_completion_status: {result.manual_evidence_completion_status}",
        f"- fields_completed_count: {result.fields_completed_count}",
        f"- remaining_missing_fields_count: {result.remaining_missing_fields_count}",
        f"- completed_evidence_groups: {result.completed_evidence_groups or 'none'}",
        f"- manual_evidence_overlay_status: {result.manual_evidence_overlay_status}",
        f"- sheets_written: {result.sheets_written}",
        f"- exported_files_count: {result.exported_files_count}",
        "- diagnostic preview only; no production prediction or betting output", "",
    ]), encoding="utf-8")
