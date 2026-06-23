# -*- coding: utf-8 -*-
"""Preview-only player impact / rolling form diagnostic layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from football_prediction_v19.analysis.player_impact_rolling_form_input_preview import PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY

PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY = "PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY"
PLAYER_FORM_DIAGNOSTIC_BLOCKED_MISSING_PLAYER_FORM_INPUT = "PLAYER_FORM_DIAGNOSTIC_BLOCKED_MISSING_PLAYER_FORM_INPUT"
PLAYER_FORM_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH = "PLAYER_FORM_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH"
PLAYER_FORM_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH = "PLAYER_FORM_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH"
PLAYER_FORM_DIAGNOSTIC_BLOCKED_UNSAFE_PATH = "PLAYER_FORM_DIAGNOSTIC_BLOCKED_UNSAFE_PATH"
PLAYER_FORM_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN = "PLAYER_FORM_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN"
PLAYER_FORM_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN = "PLAYER_FORM_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN"

OUTPUT_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team", "cross_provider_match_key",
    "player_form_evidence_status", "player_xg_xa_gate_status", "big_chance_gate_status",
    "rolling_form_gate_status", "conversion_signal_gate_status",
    "main_creator_availability_gate_status", "main_scorer_availability_gate_status",
    "no_bet_player_form_safety_status", "home_player_form_note", "away_player_form_note",
    "missing_player_form_fields_count", "missing_player_form_fields",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "player_form_diagnostic_run_id", "player_form_diagnostic_status",
    "rows_diagnosed", "player_form_evidence_status", "player_xg_xa_gate_status",
    "big_chance_gate_status", "rolling_form_gate_status", "conversion_signal_gate_status",
    "main_creator_availability_gate_status", "main_scorer_availability_gate_status",
    "no_bet_player_form_safety_status", "missing_player_form_fields_count",
    "output_path", "summary_path", "recommendation", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class PlayerFormDiagnosticConfig:
    player_impact_rolling_form_input_path: str | Path | None = None
    v19_diagnostic_gate_matrix_path: str | Path | None = None
    v19_diagnostic_synthesis_path: str | Path | None = None
    cross_provider_match_key: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/player_form_diagnostic"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class PlayerFormDiagnosticResult:
    player_form_diagnostic_run_id: str
    player_form_diagnostic_status: str
    rows_diagnosed: int
    player_form_evidence_status: str
    player_xg_xa_gate_status: str
    big_chance_gate_status: str
    rolling_form_gate_status: str
    conversion_signal_gate_status: str
    main_creator_availability_gate_status: str
    main_scorer_availability_gate_status: str
    no_bet_player_form_safety_status: str
    missing_player_form_fields_count: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class PlayerFormDiagnosticRunner:
    def __init__(self, config: PlayerFormDiagnosticConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> PlayerFormDiagnosticResult:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.player_impact_rolling_form_input_path, self.base)
        if out is None or (self.config.player_impact_rolling_form_input_path is not None and _unsafe(self.config.player_impact_rolling_form_input_path)) or (source is not None and _unsafe(source)):
            return self._blocked(PLAYER_FORM_DIAGNOSTIC_BLOCKED_UNSAFE_PATH)
        if source is None or not source.exists():
            from scripts.build_player_impact_rolling_form_input_preview import build_player_impact_rolling_form_input_preview

            player_form = build_player_impact_rolling_form_input_preview(
                cross_provider_match_key=self.config.cross_provider_match_key or "u-bundesliga-2024-001",
                output_dir=self.base / "outputs" / "analysis_preview" / "player_impact_rolling_form_input",
                base_dir=self.base,
            )
            if player_form.get("player_impact_rolling_form_input_status") != PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY:
                return self._blocked(PLAYER_FORM_DIAGNOSTIC_BLOCKED_MISSING_PLAYER_FORM_INPUT)
            source = Path(str(player_form.get("output_path", "")))
        try:
            frame = pd.read_csv(source, low_memory=False)
        except EmptyDataError:
            return self._blocked(PLAYER_FORM_DIAGNOSTIC_BLOCKED_MISSING_PLAYER_FORM_INPUT)
        selected = _select(frame, self.config.cross_provider_match_key)
        if selected.empty:
            return self._blocked(PLAYER_FORM_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(PLAYER_FORM_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH)
        diagnostic = _diagnostic_row(selected.iloc[0])
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "player_form_diagnostic.csv"
        summary_path = out / "player_form_diagnostic_summary.md"
        manifest_path = out / "player_form_diagnostic_manifest.csv"
        pd.DataFrame([diagnostic], columns=OUTPUT_COLUMNS).to_csv(output_path, index=False)
        result = PlayerFormDiagnosticResult(
            "player_form_diagnostic_preview", PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY, 1,
            str(diagnostic["player_form_evidence_status"]), str(diagnostic["player_xg_xa_gate_status"]),
            str(diagnostic["big_chance_gate_status"]), str(diagnostic["rolling_form_gate_status"]),
            str(diagnostic["conversion_signal_gate_status"]), str(diagnostic["main_creator_availability_gate_status"]),
            str(diagnostic["main_scorer_availability_gate_status"]), str(diagnostic["no_bet_player_form_safety_status"]),
            int(diagnostic["missing_player_form_fields_count"]), str(output_path.resolve()),
            str(summary_path.resolve()), str(manifest_path.resolve()),
            PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY, False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Player Form Diagnostic Preview", "",
            f"- player_form_diagnostic_status: {result.player_form_diagnostic_status}",
            f"- player_form_evidence_status: {result.player_form_evidence_status}",
            f"- player_xg_xa_gate_status: {result.player_xg_xa_gate_status}",
            f"- rolling_form_gate_status: {result.rolling_form_gate_status}",
            "- diagnostic-only player/form evidence; missing values are surfaced, not filled",
            "- no production prediction, betting output, position sizing, or financial return tracking", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str) -> PlayerFormDiagnosticResult:
        return PlayerFormDiagnosticResult(
            "player_form_diagnostic_preview", status, 0, "", "", "", "", "", "", "", "",
            0, "", "", "", status, False, False, False, False, False,
        )


def _diagnostic_row(row: pd.Series) -> dict[str, object]:
    missing_count = int(float(row.get("missing_player_form_fields_count", 0) or 0))
    evidence = "DIAGNOSTIC_READY" if missing_count == 0 else "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS"
    return {
        "match_date": row.get("match_date", ""), "competition": row.get("competition", ""),
        "season": row.get("season", ""), "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""), "cross_provider_match_key": row.get("cross_provider_match_key", ""),
        "player_form_evidence_status": evidence,
        "player_xg_xa_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_top_xg_player", "away_top_xg_player", "home_top_xa_player", "away_top_xa_player"]) else "DIAGNOSTIC_GATE_REQUIRES_PLAYER_FORM_DATA",
        "big_chance_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_big_chances_for", "away_big_chances_for", "home_big_chances_against", "away_big_chances_against"]) else "DIAGNOSTIC_GATE_REQUIRES_PLAYER_FORM_DATA",
        "rolling_form_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_recent_matches", "away_recent_matches", "home_recent_xg_for", "away_recent_xg_for"]) else "DIAGNOSTIC_GATE_REQUIRES_PLAYER_FORM_DATA",
        "conversion_signal_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_recent_conversion_note", "away_recent_conversion_note"]) else "DIAGNOSTIC_GATE_REQUIRES_PLAYER_FORM_DATA",
        "main_creator_availability_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_main_creator_status", "away_main_creator_status"]) else "DIAGNOSTIC_GATE_REQUIRES_PLAYER_FORM_DATA",
        "main_scorer_availability_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_main_scorer_status", "away_main_scorer_status"]) else "DIAGNOSTIC_GATE_REQUIRES_PLAYER_FORM_DATA",
        "no_bet_player_form_safety_status": "BETTING_OUTPUT_DISABLED_BY_DESIGN",
        "home_player_form_note": row.get("home_player_impact_note", ""),
        "away_player_form_note": row.get("away_player_impact_note", ""),
        "missing_player_form_fields_count": missing_count,
        "missing_player_form_fields": row.get("missing_player_form_fields", ""),
        "network_calls_enabled": False, "prediction_logic_enabled": False,
        "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
    }


def _select(frame: pd.DataFrame, key: str | None) -> pd.DataFrame:
    if key and "cross_provider_match_key" in frame.columns:
        return frame[frame["cross_provider_match_key"].astype(str).str.lower() == str(key).lower()]
    return frame


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "player_form_diagnostic").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""
