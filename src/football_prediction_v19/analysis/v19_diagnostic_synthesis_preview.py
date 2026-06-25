# -*- coding: utf-8 -*-
"""Diagnostic-only v1.9 synthesis preview for human report sections."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY = "V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY"
V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_INPUT = "V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_INPUT"
V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNKNOWN_MATCH = "V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNKNOWN_MATCH"
V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_AMBIGUOUS_MATCH = "V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_AMBIGUOUS_MATCH"
V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_COLUMNS = "V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_COLUMNS"
V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_VALUES = "V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_VALUES"
V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNSAFE_PATH = "V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNSAFE_PATH"
V19_DIAGNOSTIC_SYNTHESIS_OPTIONAL_VALUES_MISSING = "V19_DIAGNOSTIC_SYNTHESIS_OPTIONAL_VALUES_MISSING"
V19_DIAGNOSTIC_SYNTHESIS_NO_MODEL_INTEGRATION_BY_DESIGN = "V19_DIAGNOSTIC_SYNTHESIS_NO_MODEL_INTEGRATION_BY_DESIGN"
V19_DIAGNOSTIC_SYNTHESIS_NO_BETTING_INTEGRATION_BY_DESIGN = "V19_DIAGNOSTIC_SYNTHESIS_NO_BETTING_INTEGRATION_BY_DESIGN"
V19_DIAGNOSTIC_SYNTHESIS_NO_STAKING_INTEGRATION_BY_DESIGN = "V19_DIAGNOSTIC_SYNTHESIS_NO_STAKING_INTEGRATION_BY_DESIGN"
V19_DIAGNOSTIC_SYNTHESIS_NETWORK_DISABLED_BY_DESIGN = "V19_DIAGNOSTIC_SYNTHESIS_NETWORK_DISABLED_BY_DESIGN"

DIAGNOSTIC_COLUMNS = [
    "v19_diagnostic_synthesis_id", "analysis_input_id", "context_bundle_id", "match_date",
    "competition", "season", "home_team", "away_team", "understat_provider_match_id",
    "fbref_provider_match_id", "cross_provider_match_key", "home_xg", "away_xg",
    "home_xga", "away_xga", "home_shots", "away_shots", "home_shots_on_target",
    "away_shots_on_target", "home_possession", "away_possession",
    "home_progressive_passes", "away_progressive_passes", "home_progressive_carries",
    "away_progressive_carries", "home_touches_att_pen_area", "away_touches_att_pen_area",
    "home_tackles", "away_tackles", "home_interceptions", "away_interceptions",
    "home_blocks", "away_blocks", "home_clearances", "away_clearances",
    "v19_model_synthesis_status", "control_model_status", "chaos_score_status",
    "underdog_win_score_status", "no_bet_safety_status", "score_family_status",
    "dnb_gate_status", "over_under_gate_status", "away_favorite_degradation_status",
    "diagnostic_data_quality_status", "missing_required_fields", "missing_optional_fields",
    "blocked_reasons", "diagnostic_notes", "v19_diagnostic_synthesis_status",
    "recommendation", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "v19_diagnostic_synthesis_run_id", "context_human_input_path", "match_context_bundle_path",
    "output_path", "rows_input", "rows_diagnosed", "candidates_checked", "candidates_matched",
    "missing_required_fields_count", "missing_optional_fields_count", "blocked_reasons_count",
    "v19_diagnostic_synthesis_status", "recommendation", "notes", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
REQUIRED_COLUMNS = ["analysis_input_id", "match_date", "competition", "season", "home_team", "away_team"]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class V19DiagnosticSynthesisConfig:
    context_human_input_path: str | Path | None = None
    match_context_bundle_path: str | Path | None = None
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_diagnostic_synthesis"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19DiagnosticSynthesisResult:
    v19_diagnostic_synthesis_run_id: str
    context_human_input_path: str
    match_context_bundle_path: str
    output_path: str
    manifest_path: str
    summary_path: str
    rows_input: int
    rows_diagnosed: int
    candidates_checked: int
    candidates_matched: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    blocked_reasons_count: int
    v19_diagnostic_synthesis_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    v19_model_synthesis_status: str = ""
    control_model_status: str = ""
    chaos_score_status: str = ""
    underdog_win_score_status: str = ""
    no_bet_safety_status: str = ""
    score_family_status: str = ""
    dnb_gate_status: str = ""
    over_under_gate_status: str = ""
    away_favorite_degradation_status: str = ""


class V19DiagnosticSynthesisRunner:
    def __init__(self, config: V19DiagnosticSynthesisConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[V19DiagnosticSynthesisResult, pd.DataFrame]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or any(_unsafe(p) for p in [self.config.context_human_input_path, self.config.match_context_bundle_path] if p):
            return self._blocked(V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=DIAGNOSTIC_COLUMNS)
        source = _resolve(self.config.context_human_input_path, self.base) or self.base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
        if not source.exists():
            return self._blocked(V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_INPUT, source=source), pd.DataFrame(columns=DIAGNOSTIC_COLUMNS)
        frame = pd.read_csv(source, low_memory=False)
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing_columns:
            return self._blocked(V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_COLUMNS, source=source, rows_input=len(frame), notes=" | ".join(missing_columns)), pd.DataFrame(columns=DIAGNOSTIC_COLUMNS)
        missing_required = _missing_value_count(frame, REQUIRED_COLUMNS)
        if missing_required:
            return self._blocked(V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_VALUES, source=source, rows_input=len(frame), missing_required=missing_required), pd.DataFrame(columns=DIAGNOSTIC_COLUMNS)
        selected = _filter(frame, self.config)
        if len(selected) == 0:
            return self._blocked(V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNKNOWN_MATCH, source=source, rows_input=len(frame), checked=len(frame)), pd.DataFrame(columns=DIAGNOSTIC_COLUMNS)
        if len(selected) > 1:
            return self._blocked(V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_AMBIGUOUS_MATCH, source=source, rows_input=len(frame), checked=len(frame), matched=len(selected)), pd.DataFrame(columns=DIAGNOSTIC_COLUMNS)
        diag_row = _diagnostic_row(selected.iloc[0])
        missing_optional = len([p for p in str(diag_row["missing_optional_fields"]).split(" | ") if p])
        blocked_count = len([p for p in str(diag_row["blocked_reasons"]).split(" | ") if p])
        diag = pd.DataFrame([{**diag_row, "v19_diagnostic_synthesis_status": V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY, "recommendation": V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY, "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}], columns=DIAGNOSTIC_COLUMNS)
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "v19_diagnostic_synthesis.csv"
        manifest_path = out / "v19_diagnostic_synthesis_manifest.csv"
        summary_path = out / "v19_diagnostic_synthesis_summary.md"
        diag.to_csv(output_path, index=False)
        result = V19DiagnosticSynthesisResult("v19_diagnostic_synthesis_preview", str(source.resolve()), str(self.config.match_context_bundle_path or ""), str(output_path.resolve()), str(manifest_path.resolve()), str(summary_path.resolve()), len(frame), 1, len(frame), 1, 0, missing_optional, blocked_count, V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY, V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY, _notes(missing_optional), False, False, False, False, False, str(diag_row["v19_model_synthesis_status"]), str(diag_row["control_model_status"]), str(diag_row["chaos_score_status"]), str(diag_row["underdog_win_score_status"]), str(diag_row["no_bet_safety_status"]), str(diag_row["score_family_status"]), str(diag_row["dnb_gate_status"]), str(diag_row["over_under_gate_status"]), str(diag_row["away_favorite_degradation_status"]))
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(f"# v1.9 Diagnostic Synthesis Preview\n\n- v19_diagnostic_synthesis_status: {result.v19_diagnostic_synthesis_status}\n- betting output, position sizing, and financial return tracking disabled by design\n", encoding="utf-8")
        return result, diag

    def _blocked(self, status: str, *, source: Path | None = None, rows_input: int = 0, checked: int = 0, matched: int = 0, missing_required: int = 0, notes: str = "") -> V19DiagnosticSynthesisResult:
        return V19DiagnosticSynthesisResult("v19_diagnostic_synthesis_preview", str(source or self.config.context_human_input_path or ""), str(self.config.match_context_bundle_path or ""), "", "", "", rows_input, 0, checked, matched, missing_required, 0, 0, status, status, notes or _notes(0), False, False, False, False, False)


def _filter(frame: pd.DataFrame, config: V19DiagnosticSynthesisConfig) -> pd.DataFrame:
    selected = frame.copy()
    filters = [("cross_provider_match_key", config.cross_provider_match_key), ("understat_provider_match_id", config.understat_provider_match_id), ("fbref_provider_match_id", config.fbref_provider_match_id), ("home_team", config.home_team), ("away_team", config.away_team), ("competition", config.competition), ("season", config.season)]
    for column, value in filters:
        if value:
            selected = selected[selected[column].astype(str).str.lower() == str(value).lower()]
    if config.match_date:
        selected = selected[selected["match_date"].astype(str).str[:10] == str(config.match_date)[:10]]
    return selected


def _diagnostic_row(row: pd.Series) -> dict[str, object]:
    values = {c: row.get(c, "") for c in DIAGNOSTIC_COLUMNS}
    values["v19_diagnostic_synthesis_id"] = "v19_diagnostic_synthesis_preview"
    required_metrics = ["home_xg", "away_xg", "home_shots", "away_shots", "home_possession", "away_possession"]
    blocked = [f"{m}_missing" for m in required_metrics if _blank(row.get(m, ""))]
    readiness = "DIAGNOSTIC_READY" if not blocked else "BLOCKED_BY_MISSING_DATA"
    values.update({
        "v19_model_synthesis_status": readiness,
        "control_model_status": readiness,
        "chaos_score_status": readiness,
        "underdog_win_score_status": readiness,
        "no_bet_safety_status": "BETTING_OUTPUT_DISABLED_BY_DESIGN",
        "score_family_status": readiness,
        "dnb_gate_status": readiness,
        "over_under_gate_status": readiness,
        "away_favorite_degradation_status": readiness,
        "diagnostic_data_quality_status": "DIAGNOSTIC_PREVIEW_ONLY",
        "missing_required_fields": str(row.get("missing_required_fields", "")),
        "missing_optional_fields": str(row.get("missing_optional_fields", "")),
        "blocked_reasons": " | ".join(blocked),
        "diagnostic_notes": _notes(len([p for p in str(row.get("missing_optional_fields", "")).split(" | ") if p])),
    })
    return values


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis").resolve()
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
    notes = [V19_DIAGNOSTIC_SYNTHESIS_NETWORK_DISABLED_BY_DESIGN]
    if missing_optional:
        notes.append(V19_DIAGNOSTIC_SYNTHESIS_OPTIONAL_VALUES_MISSING)
    notes.extend([V19_DIAGNOSTIC_SYNTHESIS_NO_MODEL_INTEGRATION_BY_DESIGN, V19_DIAGNOSTIC_SYNTHESIS_NO_BETTING_INTEGRATION_BY_DESIGN, V19_DIAGNOSTIC_SYNTHESIS_NO_STAKING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
