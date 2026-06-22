# -*- coding: utf-8 -*-
"""User-facing preview runner for local match analysis reports."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.context_bundle_human_input_bridge_preview import CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
from football_prediction_v19.analysis.human_24_block_report_preview import HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY
from football_prediction_v19.analysis.match_context_bundle_preview import MATCH_CONTEXT_BUNDLE_PREVIEW_READY

MATCH_ANALYSIS_RUNNER_PREVIEW_READY = "MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
MATCH_ANALYSIS_RUNNER_BLOCKED_UNKNOWN_MATCH = "MATCH_ANALYSIS_RUNNER_BLOCKED_UNKNOWN_MATCH"
MATCH_ANALYSIS_RUNNER_BLOCKED_AMBIGUOUS_MATCH = "MATCH_ANALYSIS_RUNNER_BLOCKED_AMBIGUOUS_MATCH"
MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BUNDLE = "MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BUNDLE"
MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BRIDGE = "MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BRIDGE"
MATCH_ANALYSIS_RUNNER_BLOCKED_REPORT = "MATCH_ANALYSIS_RUNNER_BLOCKED_REPORT"
MATCH_ANALYSIS_RUNNER_BLOCKED_MISSING_REQUIRED_VALUES = "MATCH_ANALYSIS_RUNNER_BLOCKED_MISSING_REQUIRED_VALUES"
MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH = "MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH"
MATCH_ANALYSIS_RUNNER_OPTIONAL_VALUES_MISSING = "MATCH_ANALYSIS_RUNNER_OPTIONAL_VALUES_MISSING"
MATCH_ANALYSIS_RUNNER_NO_MODEL_INTEGRATION_BY_DESIGN = "MATCH_ANALYSIS_RUNNER_NO_MODEL_INTEGRATION_BY_DESIGN"
MATCH_ANALYSIS_RUNNER_NO_BETTING_INTEGRATION_BY_DESIGN = "MATCH_ANALYSIS_RUNNER_NO_BETTING_INTEGRATION_BY_DESIGN"
MATCH_ANALYSIS_RUNNER_NETWORK_DISABLED_BY_DESIGN = "MATCH_ANALYSIS_RUNNER_NETWORK_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "match_analysis_runner_run_id", "analysis_input_id", "context_bundle_id",
    "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key",
    "match_date", "competition", "season", "home_team", "away_team",
    "match_context_bundle_status", "context_bridge_status", "human_24_block_report_status",
    "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
    "odds_market_movement_input_status", "market_movement_diagnostic_status",
    "market_evidence_status", "market_movement_timing_flag",
    "lineups_availability_input_status", "availability_diagnostic_status",
    "availability_evidence_status",
    "player_impact_rolling_form_input_status", "player_form_diagnostic_status",
    "player_form_evidence_status",
    "gates_evaluated", "gates_blocked", "gates_disabled", "blocked_gate_count",
    "rows_joined", "rows_written", "rows_reported", "sections_rendered",
    "missing_required_fields_count", "missing_optional_fields_count", "report_output_path",
    "match_analysis_runner_status", "recommendation", "notes", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class MatchAnalysisRunnerConfig:
    provider_match_id: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    cross_provider_match_key: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    alias_registry: str | Path | None = None
    understat_normalized_input: str | Path | None = None
    fbref_normalized_input: str | Path | None = None
    match_context_bundle_path: str | Path | None = None
    context_human_input_path: str | Path | None = None
    include_v19_diagnostic_synthesis: bool = True
    include_v19_diagnostic_gate_matrix: bool = True
    output_dir: str | Path = "outputs/analysis_preview/match_analysis_runner"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class MatchAnalysisRunnerResult:
    match_analysis_runner_run_id: str
    analysis_input_id: str
    context_bundle_id: str
    understat_provider_match_id: str
    fbref_provider_match_id: str
    cross_provider_match_key: str
    match_date: str
    competition: str
    season: str
    home_team: str
    away_team: str
    match_context_bundle_status: str
    context_bridge_status: str
    human_24_block_report_status: str
    v19_diagnostic_synthesis_status: str
    v19_diagnostic_gate_matrix_status: str
    odds_market_movement_input_status: str
    market_movement_diagnostic_status: str
    market_evidence_status: str
    market_movement_timing_flag: str
    lineups_availability_input_status: str
    availability_diagnostic_status: str
    availability_evidence_status: str
    player_impact_rolling_form_input_status: str
    player_form_diagnostic_status: str
    player_form_evidence_status: str
    gates_evaluated: int
    gates_blocked: int
    gates_disabled: int
    blocked_gate_count: int
    rows_joined: int
    rows_written: int
    rows_reported: int
    sections_rendered: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    report_output_path: str
    manifest_path: str
    summary_path: str
    match_analysis_runner_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class MatchAnalysisRunnerPreviewRunner:
    def __init__(self, config: MatchAnalysisRunnerConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> MatchAnalysisRunnerResult:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or _has_unsafe_inputs(self.config):
            return self._blocked(MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH)
        from scripts.build_match_context_bundle_preview import build_match_context_bundle_preview
        from scripts.build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview
        from scripts.build_human_24_block_report_preview import build_human_24_block_report_preview
        from scripts.build_availability_diagnostic_preview import build_availability_diagnostic_preview
        from scripts.build_lineups_availability_input_preview import build_lineups_availability_input_preview
        from scripts.build_player_form_diagnostic_preview import build_player_form_diagnostic_preview
        from scripts.build_player_impact_rolling_form_input_preview import build_player_impact_rolling_form_input_preview
        from scripts.build_market_movement_diagnostic_preview import build_market_movement_diagnostic_preview
        from scripts.build_odds_market_movement_input_preview import build_odds_market_movement_input_preview
        from scripts.build_v19_diagnostic_gate_matrix_preview import build_v19_diagnostic_gate_matrix_preview
        from scripts.build_v19_diagnostic_synthesis_preview import build_v19_diagnostic_synthesis_preview

        bundle = build_match_context_bundle_preview(
            understat_normalized_input=self.config.understat_normalized_input,
            fbref_normalized_input=self.config.fbref_normalized_input,
            provider_match_id=self.config.provider_match_id,
            understat_provider_match_id=self.config.understat_provider_match_id,
            fbref_provider_match_id=self.config.fbref_provider_match_id,
            cross_provider_match_key=self.config.cross_provider_match_key,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            match_date=self.config.match_date,
            competition=self.config.competition,
            season=self.config.season,
            alias_registry=self.config.alias_registry,
            output_dir=self.base / "outputs" / "analysis_preview" / "match_context_bundle",
            base_dir=self.base,
        ) if not self.config.match_context_bundle_path else {"context_bundle_status": MATCH_CONTEXT_BUNDLE_PREVIEW_READY, "output_path": self.config.match_context_bundle_path, "rows_joined": 1}
        if bundle.get("context_bundle_status") != MATCH_CONTEXT_BUNDLE_PREVIEW_READY:
            return self._blocked(_map_bundle_status(str(bundle.get("context_bundle_status", ""))), match_context_bundle_status=str(bundle.get("context_bundle_status", "")))
        bridge = build_context_bundle_human_input_bridge_preview(
            match_context_bundle_path=bundle.get("output_path"),
            context_bundle_id=None,
            understat_provider_match_id=self.config.understat_provider_match_id,
            fbref_provider_match_id=self.config.fbref_provider_match_id,
            cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            match_date=self.config.match_date,
            competition=self.config.competition,
            season=self.config.season,
            output_dir=self.base / "outputs" / "analysis_preview" / "context_bundle_human_input",
            base_dir=self.base,
            build_missing=False,
        ) if not self.config.context_human_input_path else {"context_bridge_status": CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY, "human_input_output_path": self.config.context_human_input_path, "rows_written": 1}
        if bridge.get("context_bridge_status") != CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY:
            return self._blocked(_map_bridge_status(str(bridge.get("context_bridge_status", ""))), match_context_bundle_status=str(bundle.get("context_bundle_status", "")), context_bridge_status=str(bridge.get("context_bridge_status", "")))
        synthesis: dict[str, object] = {}
        gate_matrix: dict[str, object] = {}
        if self.config.include_v19_diagnostic_synthesis:
            synthesis = build_v19_diagnostic_synthesis_preview(
                context_human_input_path=bridge.get("human_input_output_path"),
                cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
                understat_provider_match_id=self.config.understat_provider_match_id,
                fbref_provider_match_id=self.config.fbref_provider_match_id,
                home_team=self.config.home_team,
                away_team=self.config.away_team,
                match_date=self.config.match_date,
                competition=self.config.competition,
                season=self.config.season,
                output_dir=self.base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
                base_dir=self.base,
                build_missing=False,
            )
        if self.config.include_v19_diagnostic_gate_matrix:
            gate_matrix = build_v19_diagnostic_gate_matrix_preview(
                v19_diagnostic_synthesis_path=synthesis.get("output_path") if synthesis else None,
                context_human_input_path=bridge.get("human_input_output_path"),
                cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
                understat_provider_match_id=self.config.understat_provider_match_id,
                fbref_provider_match_id=self.config.fbref_provider_match_id,
                home_team=self.config.home_team,
                away_team=self.config.away_team,
                match_date=self.config.match_date,
                competition=self.config.competition,
                season=self.config.season,
                output_dir=self.base / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
                base_dir=self.base,
                build_missing=not synthesis,
            )
        odds = build_odds_market_movement_input_preview(
            cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
            understat_provider_match_id=self.config.understat_provider_match_id,
            fbref_provider_match_id=self.config.fbref_provider_match_id,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            match_date=self.config.match_date,
            competition=self.config.competition,
            season=self.config.season,
            output_dir=self.base / "outputs" / "analysis_preview" / "odds_market_movement_input",
            base_dir=self.base,
        )
        market = build_market_movement_diagnostic_preview(
            cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
            odds_market_movement_input_path=odds.get("output_path"),
            v19_diagnostic_synthesis_path=synthesis.get("output_path") if synthesis else None,
            v19_diagnostic_gate_matrix_path=gate_matrix.get("gate_matrix_output_path") if gate_matrix else None,
            output_dir=self.base / "outputs" / "analysis_preview" / "market_movement_diagnostic",
            base_dir=self.base,
        )
        availability_input = build_lineups_availability_input_preview(
            cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
            understat_provider_match_id=self.config.understat_provider_match_id,
            fbref_provider_match_id=self.config.fbref_provider_match_id,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            match_date=self.config.match_date,
            competition=self.config.competition,
            season=self.config.season,
            output_dir=self.base / "outputs" / "analysis_preview" / "lineups_availability_input",
            base_dir=self.base,
        )
        availability = build_availability_diagnostic_preview(
            cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
            lineups_availability_input_path=availability_input.get("output_path"),
            v19_diagnostic_synthesis_path=synthesis.get("output_path") if synthesis else None,
            v19_diagnostic_gate_matrix_path=gate_matrix.get("gate_matrix_output_path") if gate_matrix else None,
            output_dir=self.base / "outputs" / "analysis_preview" / "availability_diagnostic",
            base_dir=self.base,
        )
        player_form_input = build_player_impact_rolling_form_input_preview(
            cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
            understat_provider_match_id=self.config.understat_provider_match_id,
            fbref_provider_match_id=self.config.fbref_provider_match_id,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            match_date=self.config.match_date,
            competition=self.config.competition,
            season=self.config.season,
            output_dir=self.base / "outputs" / "analysis_preview" / "player_impact_rolling_form_input",
            base_dir=self.base,
        )
        player_form = build_player_form_diagnostic_preview(
            cross_provider_match_key=self.config.cross_provider_match_key or self.config.provider_match_id,
            player_impact_rolling_form_input_path=player_form_input.get("output_path"),
            v19_diagnostic_synthesis_path=synthesis.get("output_path") if synthesis else None,
            v19_diagnostic_gate_matrix_path=gate_matrix.get("gate_matrix_output_path") if gate_matrix else None,
            output_dir=self.base / "outputs" / "analysis_preview" / "player_form_diagnostic",
            base_dir=self.base,
        )
        report = build_human_24_block_report_preview(
            context_human_input_path=bridge.get("human_input_output_path"),
            v19_diagnostic_synthesis_path=synthesis.get("output_path") if synthesis else None,
            v19_diagnostic_gate_matrix_path=gate_matrix.get("gate_matrix_output_path") if gate_matrix else None,
            market_movement_diagnostic_path=market.get("output_path"),
            availability_diagnostic_path=availability.get("output_path"),
            player_form_diagnostic_path=player_form.get("output_path"),
            output_dir=self.base / "outputs" / "analysis_preview" / "human_24_block_report",
            base_dir=self.base,
            build_missing=False,
        )
        if report.get("human_24_block_report_status") != HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY:
            return self._blocked(MATCH_ANALYSIS_RUNNER_BLOCKED_REPORT, match_context_bundle_status=str(bundle.get("context_bundle_status", "")), context_bridge_status=str(bridge.get("context_bridge_status", "")), human_24_block_report_status=str(report.get("human_24_block_report_status", "")))
        human = pd.read_csv(bridge["human_input_output_path"], low_memory=False).iloc[0]
        missing_optional = int(report.get("missing_optional_fields_count", 0) or bridge.get("missing_optional_fields_count", 0) or 0)
        out.mkdir(parents=True, exist_ok=True)
        manifest_path = out / "match_analysis_runner_manifest.csv"
        summary_path = out / "match_analysis_runner_summary.md"
        result = MatchAnalysisRunnerResult(
            "match_analysis_runner_preview",
            str(human.get("analysis_input_id", "")),
            str(human.get("context_bundle_id", "")),
            str(human.get("understat_provider_match_id", "")),
            str(human.get("fbref_provider_match_id", "")),
            str(human.get("cross_provider_match_key", "")),
            str(human.get("match_date", "")),
            str(human.get("competition", "")),
            str(human.get("season", "")),
            str(human.get("home_team", "")),
            str(human.get("away_team", "")),
            str(bundle.get("context_bundle_status", "")),
            str(bridge.get("context_bridge_status", "")),
            str(report.get("human_24_block_report_status", "")),
            str(synthesis.get("v19_diagnostic_synthesis_status", "")),
            str(gate_matrix.get("v19_diagnostic_gate_matrix_status", "")),
            str(odds.get("odds_market_movement_input_status", "")),
            str(market.get("market_movement_diagnostic_status", "")),
            str(market.get("market_evidence_status", "")),
            str(market.get("market_movement_timing_flag", "")),
            str(availability_input.get("lineups_availability_input_status", "")),
            str(availability.get("availability_diagnostic_status", "")),
            str(availability.get("availability_evidence_status", "")),
            str(player_form_input.get("player_impact_rolling_form_input_status", "")),
            str(player_form.get("player_form_diagnostic_status", "")),
            str(player_form.get("player_form_evidence_status", "")),
            int(gate_matrix.get("gates_evaluated", 0) or 0),
            int(gate_matrix.get("gates_blocked", 0) or 0),
            int(gate_matrix.get("gates_disabled", 0) or 0),
            int(gate_matrix.get("blocked_gate_count", 0) or 0),
            int(bundle.get("rows_joined", 0)),
            int(bridge.get("rows_written", 0)),
            int(report.get("rows_reported", 0)),
            int(report.get("sections_rendered", 0)),
            int(report.get("missing_required_fields_count", 0)),
            missing_optional,
            str(report.get("report_output_path", "")),
            str(manifest_path.resolve()),
            str(summary_path.resolve()),
            MATCH_ANALYSIS_RUNNER_PREVIEW_READY,
            MATCH_ANALYSIS_RUNNER_PREVIEW_READY,
            _notes(missing_optional),
            False,
            False,
            False,
            False,
            False,
        )
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(f"# Match Analysis Runner Preview\n\n- match_analysis_runner_status: {result.match_analysis_runner_status}\n- sections_rendered: {result.sections_rendered}\n", encoding="utf-8")
        return result

    def _blocked(self, status: str, *, match_context_bundle_status: str = "", context_bridge_status: str = "", human_24_block_report_status: str = "") -> MatchAnalysisRunnerResult:
        return MatchAnalysisRunnerResult("match_analysis_runner_preview", "", "", "", "", "", "", "", "", "", "", match_context_bundle_status, context_bridge_status, human_24_block_report_status, "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", "", "", status, status, _notes(0), False, False, False, False, False)


def _map_bundle_status(status: str) -> str:
    if "UNKNOWN" in status:
        return MATCH_ANALYSIS_RUNNER_BLOCKED_UNKNOWN_MATCH
    if "AMBIGUOUS" in status:
        return MATCH_ANALYSIS_RUNNER_BLOCKED_AMBIGUOUS_MATCH
    if "MISSING_REQUIRED" in status:
        return MATCH_ANALYSIS_RUNNER_BLOCKED_MISSING_REQUIRED_VALUES
    return MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BUNDLE


def _map_bridge_status(status: str) -> str:
    if "UNKNOWN" in status:
        return MATCH_ANALYSIS_RUNNER_BLOCKED_UNKNOWN_MATCH
    if "AMBIGUOUS" in status:
        return MATCH_ANALYSIS_RUNNER_BLOCKED_AMBIGUOUS_MATCH
    if "MISSING_REQUIRED" in status:
        return MATCH_ANALYSIS_RUNNER_BLOCKED_MISSING_REQUIRED_VALUES
    return MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BRIDGE


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "match_analysis_runner").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _has_unsafe_inputs(config: MatchAnalysisRunnerConfig) -> bool:
    for value in [config.understat_normalized_input, config.fbref_normalized_input, config.match_context_bundle_path, config.context_human_input_path, config.alias_registry]:
        if value and _unsafe(value):
            return True
    return False


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _notes(missing_optional: int) -> str:
    notes = [MATCH_ANALYSIS_RUNNER_NETWORK_DISABLED_BY_DESIGN]
    if missing_optional:
        notes.append(MATCH_ANALYSIS_RUNNER_OPTIONAL_VALUES_MISSING)
    notes.extend([MATCH_ANALYSIS_RUNNER_NO_MODEL_INTEGRATION_BY_DESIGN, MATCH_ANALYSIS_RUNNER_NO_BETTING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
