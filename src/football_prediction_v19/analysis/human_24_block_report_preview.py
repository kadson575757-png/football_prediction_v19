# -*- coding: utf-8 -*-
"""Render a preview-only 24-block human match report."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY = "HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_VALUES = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_VALUES"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH"
HUMAN_24_BLOCK_MATCH_REPORT_OPTIONAL_VALUES_MISSING = "HUMAN_24_BLOCK_MATCH_REPORT_OPTIONAL_VALUES_MISSING"
HUMAN_24_BLOCK_MATCH_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN = "HUMAN_24_BLOCK_MATCH_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN"
HUMAN_24_BLOCK_MATCH_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN = "HUMAN_24_BLOCK_MATCH_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN"
HUMAN_24_BLOCK_MATCH_REPORT_NETWORK_DISABLED_BY_DESIGN = "HUMAN_24_BLOCK_MATCH_REPORT_NETWORK_DISABLED_BY_DESIGN"

REQUIRED_SECTIONS = [
    "Screen / Data Checklist", "Match Identity", "Data Quality", "Understat xG/xGA Snapshot",
    "FBref Team / Match Stats Snapshot", "Shot Profile", "Possession Profile", "Passing Profile",
    "Progression Profile", "Defensive Actions Profile", "Home / Away Split Status",
    "Player xG / xA Status", "Lineups Status", "Injuries / Suspensions Status",
    "Recent Form Status", "H2H Status", "Contradictions / Data Gaps",
    "v1.9 Model Synthesis Status", "Control Model Status", "Chaos Score Status",
    "Underdog Win Score Status", "No-Bet / Safety List", "Score Family Status",
    "Final Preview Conclusion",
]
MANIFEST_COLUMNS = [
    "human_24_block_report_run_id", "context_human_input_path", "report_output_path",
    "v19_diagnostic_synthesis_path", "v19_diagnostic_synthesis_status",
    "v19_diagnostic_gate_matrix_path", "v19_diagnostic_gate_matrix_status",
    "market_movement_diagnostic_path", "market_movement_diagnostic_status",
    "market_evidence_status", "market_movement_timing_flag",
    "availability_diagnostic_path", "availability_diagnostic_status",
    "availability_evidence_status",
    "player_form_diagnostic_path", "player_form_diagnostic_status",
    "player_form_evidence_status",
    "tactical_matchup_diagnostic_path", "tactical_matchup_diagnostic_status",
    "tactical_evidence_status",
    "gates_evaluated", "gates_blocked", "gates_disabled", "blocked_gate_count",
    "rows_input", "rows_reported", "sections_rendered", "required_sections_rendered",
    "missing_required_fields_count", "missing_optional_fields_count",
    "human_24_block_report_status", "recommendation", "notes", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
REQUIRED_COLUMNS = ["analysis_input_id", "match_date", "competition", "season", "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id"]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class Human24BlockReportConfig:
    context_human_input_path: str | Path | None = None
    v19_diagnostic_synthesis_path: str | Path | None = None
    v19_diagnostic_gate_matrix_path: str | Path | None = None
    market_movement_diagnostic_path: str | Path | None = None
    availability_diagnostic_path: str | Path | None = None
    player_form_diagnostic_path: str | Path | None = None
    tactical_matchup_diagnostic_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/human_24_block_report"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class Human24BlockReportResult:
    human_24_block_report_run_id: str
    context_human_input_path: str
    report_output_path: str
    manifest_path: str
    v19_diagnostic_synthesis_path: str
    v19_diagnostic_synthesis_status: str
    v19_diagnostic_gate_matrix_path: str
    v19_diagnostic_gate_matrix_status: str
    market_movement_diagnostic_path: str
    market_movement_diagnostic_status: str
    market_evidence_status: str
    market_movement_timing_flag: str
    availability_diagnostic_path: str
    availability_diagnostic_status: str
    availability_evidence_status: str
    player_form_diagnostic_path: str
    player_form_diagnostic_status: str
    player_form_evidence_status: str
    tactical_matchup_diagnostic_path: str
    tactical_matchup_diagnostic_status: str
    tactical_evidence_status: str
    gates_evaluated: int
    gates_blocked: int
    gates_disabled: int
    blocked_gate_count: int
    rows_input: int
    rows_reported: int
    sections_rendered: int
    required_sections_rendered: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    human_24_block_report_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class Human24BlockReportRenderer:
    def __init__(self, config: Human24BlockReportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[Human24BlockReportResult, str]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH), ""
        source = _resolve(self.config.context_human_input_path, self.base) or self.base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
        diag_source = _resolve(self.config.v19_diagnostic_synthesis_path, self.base)
        gate_source = _resolve(self.config.v19_diagnostic_gate_matrix_path, self.base)
        market_source = _resolve(self.config.market_movement_diagnostic_path, self.base)
        availability_source = _resolve(self.config.availability_diagnostic_path, self.base)
        player_form_source = _resolve(self.config.player_form_diagnostic_path, self.base)
        tactical_source = _resolve(self.config.tactical_matchup_diagnostic_path, self.base)
        if _unsafe(source) or (diag_source is not None and _unsafe(diag_source)) or (gate_source is not None and _unsafe(gate_source)) or (market_source is not None and _unsafe(market_source)) or (availability_source is not None and _unsafe(availability_source)) or (player_form_source is not None and _unsafe(player_form_source)) or (tactical_source is not None and _unsafe(tactical_source)):
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH, source=source), ""
        if not source.exists():
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT, source=source), ""
        frame = pd.read_csv(source, low_memory=False)
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing_columns:
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS, source=source, rows_input=len(frame), notes=" | ".join(missing_columns)), ""
        missing_required = _missing_value_count(frame, REQUIRED_COLUMNS)
        if missing_required or len(frame) != 1:
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_VALUES, source=source, rows_input=len(frame), missing_required=missing_required), ""
        row = frame.iloc[0]
        missing_optional = len([p for p in str(row.get("missing_optional_fields", "")).split(" | ") if p])
        diagnostic = _load_diagnostic(diag_source, row)
        gate_summary = _load_gate_matrix(gate_source, row)
        market_summary = _load_market_movement(market_source, row)
        availability_summary = _load_availability(availability_source, row)
        player_form_summary = _load_player_form(player_form_source, row)
        tactical_summary = _load_tactical(tactical_source, row)
        report = _render(row, diagnostic, gate_summary, market_summary, availability_summary, player_form_summary, tactical_summary)
        rendered = sum(1 for section in REQUIRED_SECTIONS if f"## {section}" in report)
        out.mkdir(parents=True, exist_ok=True)
        report_path = out / "human_24_block_match_report_preview.md"
        manifest_path = out / "human_24_block_match_report_manifest.csv"
        report_path.write_text(report, encoding="utf-8")
        result = Human24BlockReportResult(
            human_24_block_report_run_id="human_24_block_report_preview",
            context_human_input_path=str(source.resolve()),
            report_output_path=str(report_path.resolve()),
            manifest_path=str(manifest_path.resolve()),
            v19_diagnostic_synthesis_path=str(diag_source.resolve()) if diag_source and diag_source.exists() else "",
            v19_diagnostic_synthesis_status=str(diagnostic.get("v19_diagnostic_synthesis_status", "not executed in this preview layer")),
            v19_diagnostic_gate_matrix_path=str(gate_source.resolve()) if gate_source and gate_source.exists() else "",
            v19_diagnostic_gate_matrix_status=str(gate_summary.get("v19_diagnostic_gate_matrix_status", "not executed in this preview layer")),
            market_movement_diagnostic_path=str(market_source.resolve()) if market_source and market_source.exists() else "",
            market_movement_diagnostic_status=str(market_summary.get("market_movement_diagnostic_status", "not executed in this preview layer")),
            market_evidence_status=str(market_summary.get("market_evidence_status", "not executed in this preview layer")),
            market_movement_timing_flag=str(market_summary.get("market_movement_timing_flag", "not executed in this preview layer")),
            availability_diagnostic_path=str(availability_source.resolve()) if availability_source and availability_source.exists() else "",
            availability_diagnostic_status=str(availability_summary.get("availability_diagnostic_status", "not executed in this preview layer")),
            availability_evidence_status=str(availability_summary.get("availability_evidence_status", "not executed in this preview layer")),
            player_form_diagnostic_path=str(player_form_source.resolve()) if player_form_source and player_form_source.exists() else "",
            player_form_diagnostic_status=str(player_form_summary.get("player_form_diagnostic_status", "not executed in this preview layer")),
            player_form_evidence_status=str(player_form_summary.get("player_form_evidence_status", "not executed in this preview layer")),
            tactical_matchup_diagnostic_path=str(tactical_source.resolve()) if tactical_source and tactical_source.exists() else "",
            tactical_matchup_diagnostic_status=str(tactical_summary.get("tactical_matchup_diagnostic_status", "not executed in this preview layer")),
            tactical_evidence_status=str(tactical_summary.get("tactical_evidence_status", "not executed in this preview layer")),
            gates_evaluated=int(gate_summary.get("gates_evaluated", 0) or 0),
            gates_blocked=int(gate_summary.get("gates_blocked", 0) or 0),
            gates_disabled=int(gate_summary.get("gates_disabled", 0) or 0),
            blocked_gate_count=int(gate_summary.get("blocked_gate_count", 0) or 0),
            rows_input=len(frame),
            rows_reported=1,
            sections_rendered=len(REQUIRED_SECTIONS),
            required_sections_rendered=rendered,
            missing_required_fields_count=0,
            missing_optional_fields_count=missing_optional,
            human_24_block_report_status=HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY,
            recommendation=HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY,
            notes=_notes(missing_optional),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            staking_logic_enabled=False,
            roi_logic_enabled=False,
        )
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        return result, report

    def _blocked(self, status: str, *, source: Path | None = None, rows_input: int = 0, missing_required: int = 0, notes: str = "") -> Human24BlockReportResult:
        return Human24BlockReportResult("human_24_block_report_preview", str(source or self.config.context_human_input_path or ""), "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, 0, 0, rows_input, 0, 0, 0, missing_required, 0, status, status, notes or _notes(0), False, False, False, False, False)


def _render(row: pd.Series, diagnostic: dict[str, object] | None = None, gate_summary: dict[str, object] | None = None, market_summary: dict[str, object] | None = None, availability_summary: dict[str, object] | None = None, player_form_summary: dict[str, object] | None = None, tactical_summary: dict[str, object] | None = None) -> str:
    def v(column: str) -> str:
        value = row.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return "not provided"
        return str(value)

    unavailable = "not available in this preview layer"
    not_executed = "not executed in this preview layer"
    diagnostic = diagnostic or {}
    gate_summary = gate_summary or {}
    market_summary = market_summary or {}
    availability_summary = availability_summary or {}
    player_form_summary = player_form_summary or {}
    tactical_summary = tactical_summary or {}

    def d(column: str) -> str:
        value = diagnostic.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return not_executed
        return str(value)

    def g(group: str) -> str:
        value = gate_summary.get(f"{group}_summary", "")
        if pd.isna(value) or str(value).strip() == "":
            return "Gate matrix not executed in this preview layer."
        return str(value)

    def m(column: str) -> str:
        value = market_summary.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return not_executed
        return str(value)

    def a(column: str) -> str:
        value = availability_summary.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return not_executed
        return str(value)

    def p(column: str) -> str:
        value = player_form_summary.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return not_executed
        return str(value)

    def t(column: str) -> str:
        value = tactical_summary.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return not_executed
        return str(value)

    disabled_text = "Betting output is disabled in this diagnostic preview layer. Position sizing and financial return tracking are disabled."
    gate_disabled_text = "Betting output is disabled in this diagnostic gate preview layer. Position sizing and financial return tracking are disabled."
    bodies = {
        "Screen / Data Checklist": f"Local preview context loaded. Missing optional fields: {v('missing_optional_fields')}.",
        "Match Identity": f"{v('home_team')} vs {v('away_team')} on {v('match_date')} ({v('competition')} {v('season')}).",
        "Data Quality": f"Understat: {v('understat_data_quality_status')}; FBref: {v('fbref_data_quality_status')}; context: {v('context_data_quality_status')}. Market movement diagnostic: {m('market_evidence_status')} ({m('market_movement_timing_flag')}). Availability diagnostic: {a('availability_evidence_status')}. Player/form diagnostic: {p('player_form_evidence_status')}. Tactical diagnostic: {t('tactical_evidence_status')}.",
        "Understat xG/xGA Snapshot": f"Home xG {v('home_xg')} / Away xG {v('away_xg')}; Home xGA {v('home_xga')} / Away xGA {v('away_xga')}.",
        "FBref Team / Match Stats Snapshot": f"Possession {v('home_possession')} - {v('away_possession')}; shots {v('home_shots')} - {v('away_shots')}.",
        "Shot Profile": f"Shots on target {v('home_shots_on_target')} - {v('away_shots_on_target')}.",
        "Possession Profile": f"Possession split {v('home_possession')} - {v('away_possession')}. Tactical matchup status: {t('tactical_matchup_diagnostic_status')}; score gate: {t('tactical_matchup_score_gate_status')}.",
        "Passing Profile": f"Pass completion {v('home_pass_completion_pct')} - {v('away_pass_completion_pct')}.",
        "Progression Profile": f"Progressive passes {v('home_progressive_passes')} - {v('away_progressive_passes')}; carries {v('home_progressive_carries')} - {v('away_progressive_carries')}.",
        "Defensive Actions Profile": f"Tackles {v('home_tackles')} - {v('away_tackles')}; interceptions {v('home_interceptions')} - {v('away_interceptions')}; blocks {v('home_blocks')} - {v('away_blocks')}. Transition gate: {t('transition_matchup_gate_status')}.",
        "Home / Away Split Status": unavailable,
        "Player xG / xA Status": f"Player/form diagnostic status: {p('player_form_diagnostic_status')}. xG/xA gate: {p('player_xg_xa_gate_status')}; big chance gate: {p('big_chance_gate_status')}. Home note: {p('home_player_form_note')}. Away note: {p('away_player_form_note')}.",
        "Lineups Status": f"Availability diagnostic status: {a('availability_diagnostic_status')}. Lineup gate: {a('lineup_confirmation_gate_status')}; formation gate: {a('formation_availability_gate_status')}. Home note: {a('home_availability_note')}. Away note: {a('away_availability_note')}.",
        "Injuries / Suspensions Status": f"Injuries and suspensions gate: {a('injuries_suspensions_gate_status')}; goalkeeper gate: {a('goalkeeper_availability_gate_status')}; key absence gate: {a('key_absence_gate_status')}.",
        "Recent Form Status": f"Rolling form gate: {p('rolling_form_gate_status')}; conversion signal gate: {p('conversion_signal_gate_status')}; creator gate: {p('main_creator_availability_gate_status')}; scorer gate: {p('main_scorer_availability_gate_status')}. Fatigue gate: {t('fatigue_modifier_gate_status')}.",
        "H2H Status": unavailable,
        "Contradictions / Data Gaps": f"Preview gaps are surfaced, not filled: {v('missing_optional_fields')}. Missing market fields: {m('missing_market_fields')}. Missing availability fields: {a('missing_availability_fields')}. Missing player/form fields: {p('missing_player_form_fields')}. Missing tactical fields: {t('missing_tactical_fields')}.",
        "v1.9 Model Synthesis Status": f"{d('v19_model_synthesis_status')}. {g('model')}. Production prediction logic is disabled by design.",
        "Control Model Status": f"{d('control_model_status')}. {g('control')} Tactical matchup note: {t('tactical_matchup_note')}.",
        "Chaos Score Status": f"{d('chaos_score_status')}. {g('chaos')} xG-zone correction gate: {t('xg_zone_correction_gate_status')}.",
        "Underdog Win Score Status": f"{d('underdog_win_score_status')}. {g('underdog')}",
        "No-Bet / Safety List": f"{d('no_bet_safety_status')}. {g('safety')} Market safety: {m('no_bet_market_safety_status')}. Availability safety: {a('no_bet_availability_safety_status')}. Player/form safety: {p('no_bet_player_form_safety_status')}. Tactical safety: {t('no_bet_tactical_safety_status')}. {disabled_text} {gate_disabled_text}",
        "Score Family Status": f"{d('score_family_status')}; DNB gate: {d('dnb_gate_status')}; over/under gate: {d('over_under_gate_status')}; away favorite degradation: {d('away_favorite_degradation_status')}. Market gates: odds={m('odds_availability_gate_status')}; DNB={m('dnb_market_availability_status')}; over/under={m('over_under_market_availability_status')}. Set-piece ratio gate: {t('set_piece_xg_ratio_gate_status')}. Formation gate: {t('formation_matchup_gate_status')}. {g('score_family')}",
        "Final Preview Conclusion": f"{HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY}. v1.9 synthesis status: {d('v19_diagnostic_synthesis_status')}. Gate matrix status: {gate_summary.get('v19_diagnostic_gate_matrix_status', not_executed)}. Market movement diagnostic status: {m('market_movement_diagnostic_status')}. Availability diagnostic status: {a('availability_diagnostic_status')}. Player/form diagnostic status: {p('player_form_diagnostic_status')}. Tactical diagnostic status: {t('tactical_matchup_diagnostic_status')}. Gates evaluated: {gate_summary.get('gates_evaluated', 0)}; blocked gates: {gate_summary.get('gates_blocked', 0)}; disabled gates: {gate_summary.get('gates_disabled', 0)}. Diagnostic only; no production model output is activated.",
    }
    lines = ["# 24-Block Human Match Report Preview", ""]
    for section in REQUIRED_SECTIONS:
        lines.extend([f"## {section}", "", bodies[section], ""])
    return "\n".join(lines)


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "human_24_block_report").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _load_diagnostic(path: Path | None, row: pd.Series) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except EmptyDataError:
        return {}
    if frame.empty:
        return {}
    selected = frame.copy()
    for column in ["analysis_input_id", "cross_provider_match_key", "understat_provider_match_id", "fbref_provider_match_id"]:
        value = row.get(column, "")
        if column in selected.columns and not _blank(value):
            narrowed = selected[selected[column].astype(str).str.lower() == str(value).lower()]
            if len(narrowed) == 1:
                return narrowed.iloc[0].to_dict()
    if len(selected) == 1:
        return selected.iloc[0].to_dict()
    return {}


def _load_gate_matrix(path: Path | None, row: pd.Series) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except EmptyDataError:
        return {}
    if frame.empty:
        return {}
    selected = frame.copy()
    for column in ["analysis_input_id", "cross_provider_match_key", "understat_provider_match_id", "fbref_provider_match_id"]:
        value = row.get(column, "")
        if column in selected.columns and not _blank(value):
            narrowed = selected[selected[column].astype(str).str.lower() == str(value).lower()]
            if not narrowed.empty:
                selected = narrowed
                break
    status_counts = selected["gate_status"].astype(str).value_counts().to_dict() if "gate_status" in selected.columns else {}
    blocked_statuses = {"DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA", "DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE"}
    disabled_statuses = {"DIAGNOSTIC_GATE_DISABLED_NO_BETTING", "DIAGNOSTIC_GATE_BLOCKED_BY_DESIGN"}
    summary: dict[str, object] = {
        "v19_diagnostic_gate_matrix_status": "V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY",
        "gates_evaluated": len(selected),
        "gates_blocked": int(sum(status_counts.get(s, 0) for s in blocked_statuses)),
        "gates_disabled": int(sum(status_counts.get(s, 0) for s in disabled_statuses)),
        "blocked_gate_count": int(sum(status_counts.get(s, 0) for s in blocked_statuses)),
    }
    groups = {
        "model": ["hard_1x2_control_model_gate", "dnb_5_plus_1_readiness_gate", "away_favorite_degradation_gate", "cellar_duel_over_lock_gate"],
        "control": ["hard_1x2_control_model_gate"],
        "chaos": ["chaos_score_gate"],
        "underdog": ["underdog_win_score_gate"],
        "safety": ["no_bet_safety_gate"],
        "score_family": ["score_family_readiness_gate", "dnb_5_plus_1_readiness_gate", "away_favorite_degradation_gate"],
    }
    for key, gate_ids in groups.items():
        subset = selected[selected["gate_id"].isin(gate_ids)] if "gate_id" in selected.columns else pd.DataFrame()
        summary[f"{key}_summary"] = _format_gate_summary(subset)
    return summary


def _load_market_movement(path: Path | None, row: pd.Series) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except EmptyDataError:
        return {}
    if frame.empty:
        return {}
    selected = frame.copy()
    for column in ["cross_provider_match_key", "understat_provider_match_id", "fbref_provider_match_id"]:
        value = row.get(column, "")
        if column in selected.columns and not _blank(value):
            narrowed = selected[selected[column].astype(str).str.lower() == str(value).lower()]
            if len(narrowed) == 1:
                selected = narrowed
                break
    if len(selected) != 1:
        return {}
    data = selected.iloc[0].to_dict()
    data["market_movement_diagnostic_status"] = "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    return data


def _load_availability(path: Path | None, row: pd.Series) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except EmptyDataError:
        return {}
    if frame.empty:
        return {}
    selected = frame.copy()
    key = row.get("cross_provider_match_key", "")
    if "cross_provider_match_key" in selected.columns and not _blank(key):
        narrowed = selected[selected["cross_provider_match_key"].astype(str).str.lower() == str(key).lower()]
        if len(narrowed) == 1:
            selected = narrowed
    if len(selected) != 1:
        return {}
    data = selected.iloc[0].to_dict()
    data["availability_diagnostic_status"] = "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
    return data


def _load_player_form(path: Path | None, row: pd.Series) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except EmptyDataError:
        return {}
    if frame.empty:
        return {}
    selected = frame.copy()
    key = row.get("cross_provider_match_key", "")
    if "cross_provider_match_key" in selected.columns and not _blank(key):
        narrowed = selected[selected["cross_provider_match_key"].astype(str).str.lower() == str(key).lower()]
        if len(narrowed) == 1:
            selected = narrowed
    if len(selected) != 1:
        return {}
    data = selected.iloc[0].to_dict()
    data["player_form_diagnostic_status"] = "PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY"
    return data


def _load_tactical(path: Path | None, row: pd.Series) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except EmptyDataError:
        return {}
    if frame.empty:
        return {}
    selected = frame.copy()
    key = row.get("cross_provider_match_key", "")
    if "cross_provider_match_key" in selected.columns and not _blank(key):
        narrowed = selected[selected["cross_provider_match_key"].astype(str).str.lower() == str(key).lower()]
        if len(narrowed) == 1:
            selected = narrowed
    if len(selected) != 1:
        return {}
    data = selected.iloc[0].to_dict()
    data["tactical_matchup_diagnostic_status"] = "TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY"
    return data


def _format_gate_summary(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "Gate matrix not available for this section."
    pieces = []
    for _, gate in frame.iterrows():
        missing = str(gate.get("missing_data", "")).strip()
        blocker = str(gate.get("blocker_reason", "")).strip()
        detail = f"{gate.get('gate_id', '')}: {gate.get('gate_status', '')}"
        if missing:
            detail += f" missing_data={missing}"
        if blocker:
            detail += f" blocker={blocker}"
        pieces.append(detail)
    return "Gate matrix diagnostics: " + "; ".join(pieces)


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _missing_value_count(frame: pd.DataFrame, columns: list[str]) -> int:
    if frame.empty:
        return 0
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        mask = mask | frame[column].isna() | frame[column].astype(str).str.strip().eq("")
    return int(mask.sum())


def _notes(missing_optional: int) -> str:
    notes = [HUMAN_24_BLOCK_MATCH_REPORT_NETWORK_DISABLED_BY_DESIGN]
    if missing_optional:
        notes.append(HUMAN_24_BLOCK_MATCH_REPORT_OPTIONAL_VALUES_MISSING)
    notes.extend([HUMAN_24_BLOCK_MATCH_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN, HUMAN_24_BLOCK_MATCH_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
