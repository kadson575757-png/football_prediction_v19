# -*- coding: utf-8 -*-
"""Diagnostic-only v1.9 gate matrix preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY = "V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY"
V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_INPUT = "V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_INPUT"
V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNKNOWN_MATCH = "V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNKNOWN_MATCH"
V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_AMBIGUOUS_MATCH = "V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_AMBIGUOUS_MATCH"
V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_COLUMNS = "V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_COLUMNS"
V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_VALUES = "V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_VALUES"
V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNSAFE_PATH = "V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNSAFE_PATH"
V19_DIAGNOSTIC_GATE_MATRIX_OPTIONAL_VALUES_MISSING = "V19_DIAGNOSTIC_GATE_MATRIX_OPTIONAL_VALUES_MISSING"
V19_DIAGNOSTIC_GATE_MATRIX_NO_MODEL_INTEGRATION_BY_DESIGN = "V19_DIAGNOSTIC_GATE_MATRIX_NO_MODEL_INTEGRATION_BY_DESIGN"
V19_DIAGNOSTIC_GATE_MATRIX_NO_BETTING_INTEGRATION_BY_DESIGN = "V19_DIAGNOSTIC_GATE_MATRIX_NO_BETTING_INTEGRATION_BY_DESIGN"
V19_DIAGNOSTIC_GATE_MATRIX_NO_STAKING_INTEGRATION_BY_DESIGN = "V19_DIAGNOSTIC_GATE_MATRIX_NO_STAKING_INTEGRATION_BY_DESIGN"
V19_DIAGNOSTIC_GATE_MATRIX_NETWORK_DISABLED_BY_DESIGN = "V19_DIAGNOSTIC_GATE_MATRIX_NETWORK_DISABLED_BY_DESIGN"

DIAGNOSTIC_GATE_READY = "DIAGNOSTIC_GATE_READY"
DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA = "DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA"
DIAGNOSTIC_GATE_BLOCKED_BY_DESIGN = "DIAGNOSTIC_GATE_BLOCKED_BY_DESIGN"
DIAGNOSTIC_GATE_DISABLED_NO_BETTING = "DIAGNOSTIC_GATE_DISABLED_NO_BETTING"
DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE = "DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE"
DIAGNOSTIC_GATE_OPTIONAL_DATA_MISSING = "DIAGNOSTIC_GATE_OPTIONAL_DATA_MISSING"

GATE_MATRIX_COLUMNS = [
    "gate_matrix_id", "v19_diagnostic_synthesis_id", "analysis_input_id", "context_bundle_id",
    "match_date", "competition", "season", "home_team", "away_team",
    "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key",
    "gate_id", "gate_name", "gate_group", "gate_status", "gate_severity",
    "required_data", "available_data", "missing_data", "blocker_reason",
    "diagnostic_note", "safe_output_note", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "v19_diagnostic_gate_matrix_run_id", "v19_diagnostic_synthesis_path",
    "context_human_input_path", "gate_matrix_output_path", "rows_input",
    "gates_evaluated", "gates_ready", "gates_blocked", "gates_disabled",
    "gates_missing_optional_data", "candidates_checked", "candidates_matched",
    "missing_required_fields_count", "missing_optional_fields_count",
    "blocked_gate_count", "v19_diagnostic_gate_matrix_status", "recommendation",
    "notes", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
REQUIRED_COLUMNS = [
    "analysis_input_id", "match_date", "competition", "season", "home_team",
    "away_team",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]
GATE_DEFINITIONS = [
    ("hard_1x2_control_model_gate", "Hard 1X2 Control Model Gate", "control", ["home_xg", "away_xg", "home_shots", "away_shots"]),
    ("dnb_5_plus_1_readiness_gate", "DNB 5+1 Readiness Gate", "dnb", ["home_xg", "away_xg", "home_possession", "away_possession"]),
    ("away_favorite_degradation_gate", "Away Favorite Degradation Gate", "favorite_degradation", ["away_xg", "away_shots", "away_possession"]),
    ("cellar_duel_over_lock_gate", "Cellar Duel Over Lock Gate", "over_under", ["home_xg", "away_xg", "home_shots_on_target", "away_shots_on_target"]),
    ("tactical_matchup_score_gate", "Tactical Matchup Score Gate", "tactical", ["home_progressive_passes", "away_progressive_passes", "home_progressive_carries", "away_progressive_carries"]),
    ("set_piece_xg_ratio_gate", "Set Piece xG Ratio Gate", "set_piece", ["home_set_piece_xg", "away_set_piece_xg"]),
    ("do_so_fatigue_modifier_gate", "DO/SO Fatigue Modifier Gate", "fatigue", ["rest_days_home", "rest_days_away"]),
    ("market_movement_timing_gate", "Market Movement Timing Gate", "market", ["odds_home", "odds_draw", "odds_away"]),
    ("xg_zone_correction_gate", "xG Zone Correction Gate", "xg_zone", ["home_touches_att_pen_area", "away_touches_att_pen_area"]),
    ("no_bet_safety_gate", "No-Bet Safety Gate", "safety", []),
    ("chaos_score_gate", "Chaos Score Gate", "chaos", ["home_blocks", "away_blocks", "home_clearances", "away_clearances"]),
    ("underdog_win_score_gate", "Underdog Win Score Gate", "underdog", ["home_xg", "away_xg", "home_shots", "away_shots"]),
    ("score_family_readiness_gate", "Score Family Readiness Gate", "score_family", ["home_xg", "away_xg", "home_shots_on_target", "away_shots_on_target"]),
    ("lineup_availability_gate", "Lineup Availability Gate", "lineups", ["home_lineup_status", "away_lineup_status"]),
    ("injuries_suspensions_gate", "Injuries Suspensions Gate", "availability", ["home_injuries_status", "away_injuries_status"]),
    ("recent_form_gate", "Recent Form Gate", "form", ["home_recent_form", "away_recent_form"]),
    ("h2h_context_gate", "H2H Context Gate", "h2h", ["h2h_context_status"]),
    ("player_xg_xa_gate", "Player xG/xA Gate", "player", ["home_player_xg_status", "away_player_xg_status"]),
    ("odds_market_availability_gate", "Odds Market Availability Gate", "market", ["odds_home", "odds_draw", "odds_away"]),
]


@dataclass(frozen=True)
class V19DiagnosticGateMatrixConfig:
    v19_diagnostic_synthesis_path: str | Path | None = None
    context_human_input_path: str | Path | None = None
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_diagnostic_gate_matrix"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19DiagnosticGateMatrixResult:
    v19_diagnostic_gate_matrix_run_id: str
    v19_diagnostic_synthesis_path: str
    context_human_input_path: str
    gate_matrix_output_path: str
    manifest_path: str
    summary_path: str
    rows_input: int
    gates_evaluated: int
    gates_ready: int
    gates_blocked: int
    gates_disabled: int
    gates_missing_optional_data: int
    candidates_checked: int
    candidates_matched: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    blocked_gate_count: int
    v19_diagnostic_gate_matrix_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class V19DiagnosticGateMatrixRunner:
    def __init__(self, config: V19DiagnosticGateMatrixConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[V19DiagnosticGateMatrixResult, pd.DataFrame]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or any(_unsafe(p) for p in [self.config.v19_diagnostic_synthesis_path, self.config.context_human_input_path] if p):
            return self._blocked(V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=GATE_MATRIX_COLUMNS)
        source = _resolve(self.config.v19_diagnostic_synthesis_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis" / "v19_diagnostic_synthesis.csv"
        if source is None or not source.exists() or source.is_dir():
            return self._blocked(V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_INPUT, source=source), pd.DataFrame(columns=GATE_MATRIX_COLUMNS)
        frame = pd.read_csv(source, low_memory=False)
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing_columns:
            return self._blocked(V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_COLUMNS, source=source, rows_input=len(frame), notes=" | ".join(missing_columns)), pd.DataFrame(columns=GATE_MATRIX_COLUMNS)
        missing_required = _missing_value_count(frame, REQUIRED_COLUMNS)
        if missing_required:
            return self._blocked(V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_VALUES, source=source, rows_input=len(frame), missing_required=missing_required), pd.DataFrame(columns=GATE_MATRIX_COLUMNS)
        selected = _filter(frame, self.config)
        if len(selected) == 0:
            return self._blocked(V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNKNOWN_MATCH, source=source, rows_input=len(frame), checked=len(frame)), pd.DataFrame(columns=GATE_MATRIX_COLUMNS)
        if len(selected) > 1:
            return self._blocked(V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_AMBIGUOUS_MATCH, source=source, rows_input=len(frame), checked=len(frame), matched=len(selected)), pd.DataFrame(columns=GATE_MATRIX_COLUMNS)
        row = selected.iloc[0]
        gate_rows = [_gate_row(row, gate) for gate in GATE_DEFINITIONS]
        table = pd.DataFrame(gate_rows, columns=GATE_MATRIX_COLUMNS)
        gates_ready = int((table["gate_status"] == DIAGNOSTIC_GATE_READY).sum())
        gates_blocked = int(table["gate_status"].isin([DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA, DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE]).sum())
        gates_disabled = int(table["gate_status"].isin([DIAGNOSTIC_GATE_DISABLED_NO_BETTING, DIAGNOSTIC_GATE_BLOCKED_BY_DESIGN]).sum())
        gates_missing_optional = int((table["gate_status"] == DIAGNOSTIC_GATE_OPTIONAL_DATA_MISSING).sum())
        missing_optional = len([p for p in str(row.get("missing_optional_fields", "")).split(" | ") if p])
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "v19_diagnostic_gate_matrix.csv"
        manifest_path = out / "v19_diagnostic_gate_matrix_manifest.csv"
        summary_path = out / "v19_diagnostic_gate_matrix_summary.md"
        table.to_csv(output_path, index=False)
        result = V19DiagnosticGateMatrixResult(
            "v19_diagnostic_gate_matrix_preview", str(source.resolve()),
            str(self.config.context_human_input_path or ""), str(output_path.resolve()),
            str(manifest_path.resolve()), str(summary_path.resolve()), len(frame),
            len(table), gates_ready, gates_blocked, gates_disabled, gates_missing_optional,
            len(frame), 1, 0, missing_optional, gates_blocked,
            V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY, V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY,
            _notes(missing_optional), False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(
            "\n".join([
                "# v1.9 Diagnostic Gate Matrix Preview",
                "",
                f"- v19_diagnostic_gate_matrix_status: {result.v19_diagnostic_gate_matrix_status}",
                f"- gates_evaluated: {result.gates_evaluated}",
                f"- gates_ready: {result.gates_ready}",
                f"- gates_blocked: {result.gates_blocked}",
                "- betting output, position sizing, and financial return tracking disabled by design",
                "",
            ]),
            encoding="utf-8",
        )
        return result, table

    def _blocked(self, status: str, *, source: Path | None = None, rows_input: int = 0, checked: int = 0, matched: int = 0, missing_required: int = 0, notes: str = "") -> V19DiagnosticGateMatrixResult:
        return V19DiagnosticGateMatrixResult("v19_diagnostic_gate_matrix_preview", str(source or self.config.v19_diagnostic_synthesis_path or ""), str(self.config.context_human_input_path or ""), "", "", "", rows_input, 0, 0, 0, 0, 0, checked, matched, missing_required, 0, 0, status, status, notes or _notes(0), False, False, False, False, False)


def _gate_row(row: pd.Series, gate: tuple[str, str, str, list[str]]) -> dict[str, object]:
    gate_id, gate_name, gate_group, required = gate
    available = [field for field in required if not _blank(row.get(field, ""))]
    missing = [field for field in required if field not in row.index or _blank(row.get(field, ""))]
    if gate_id == "no_bet_safety_gate":
        status = DIAGNOSTIC_GATE_DISABLED_NO_BETTING
        severity = "safety"
        blocker = "betting_output_disabled_by_design"
    elif missing and gate_group in {"lineups", "availability", "form", "h2h", "player", "fatigue", "market", "set_piece"}:
        status = DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE
        severity = "info"
        blocker = "requires_later_model_phase_or_unavailable_preview_data"
    elif missing:
        status = DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA
        severity = "warning"
        blocker = "missing_required_preview_data"
    else:
        status = DIAGNOSTIC_GATE_READY
        severity = "diagnostic"
        blocker = ""
    identity = {c: row.get(c, "") for c in ["analysis_input_id", "context_bundle_id", "match_date", "competition", "season", "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key"]}
    return {
        **identity,
        "gate_matrix_id": "v19_diagnostic_gate_matrix_preview",
        "v19_diagnostic_synthesis_id": row.get("v19_diagnostic_synthesis_id", ""),
        "gate_id": gate_id,
        "gate_name": gate_name,
        "gate_group": gate_group,
        "gate_status": status,
        "gate_severity": severity,
        "required_data": " | ".join(required),
        "available_data": " | ".join(available),
        "missing_data": " | ".join(missing),
        "blocker_reason": blocker,
        "diagnostic_note": "Diagnostic gate status only; no production prediction or final market output is generated.",
        "safe_output_note": "No betting output, position sizing, units, or financial return tracking is generated.",
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _filter(frame: pd.DataFrame, config: V19DiagnosticGateMatrixConfig) -> pd.DataFrame:
    selected = frame.copy()
    for column, value in [("cross_provider_match_key", config.cross_provider_match_key), ("understat_provider_match_id", config.understat_provider_match_id), ("fbref_provider_match_id", config.fbref_provider_match_id), ("home_team", config.home_team), ("away_team", config.away_team), ("competition", config.competition), ("season", config.season)]:
        if value:
            selected = selected[selected[column].astype(str).str.lower() == str(value).lower()]
    if config.match_date:
        selected = selected[selected["match_date"].astype(str).str[:10] == str(config.match_date)[:10]]
    return selected


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    if str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _missing_value_count(frame: pd.DataFrame, columns: list[str]) -> int:
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        mask = mask | frame[column].isna() | frame[column].astype(str).str.strip().eq("")
    return int(mask.sum())


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _notes(missing_optional: int) -> str:
    notes = [V19_DIAGNOSTIC_GATE_MATRIX_NETWORK_DISABLED_BY_DESIGN]
    if missing_optional:
        notes.append(V19_DIAGNOSTIC_GATE_MATRIX_OPTIONAL_VALUES_MISSING)
    notes.extend([V19_DIAGNOSTIC_GATE_MATRIX_NO_MODEL_INTEGRATION_BY_DESIGN, V19_DIAGNOSTIC_GATE_MATRIX_NO_BETTING_INTEGRATION_BY_DESIGN, V19_DIAGNOSTIC_GATE_MATRIX_NO_STAKING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
