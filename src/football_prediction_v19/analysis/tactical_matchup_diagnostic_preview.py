# -*- coding: utf-8 -*-
"""Preview-only tactical matchup diagnostic layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from football_prediction_v19.analysis.tactical_set_piece_fatigue_input_preview import TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY

TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY = "TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY"
TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_MISSING_TACTICAL_INPUT = "TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_MISSING_TACTICAL_INPUT"
TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH = "TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH"
TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH = "TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH"
TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_UNSAFE_PATH = "TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_UNSAFE_PATH"
TACTICAL_MATCHUP_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN = "TACTICAL_MATCHUP_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN"
TACTICAL_MATCHUP_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN = "TACTICAL_MATCHUP_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN"

OUTPUT_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team", "cross_provider_match_key",
    "tactical_evidence_status", "set_piece_xg_ratio_gate_status",
    "tactical_matchup_score_gate_status", "fatigue_modifier_gate_status",
    "xg_zone_correction_gate_status", "formation_matchup_gate_status",
    "transition_matchup_gate_status", "no_bet_tactical_safety_status",
    "home_tactical_note", "away_tactical_note", "tactical_matchup_note",
    "missing_tactical_fields_count", "missing_tactical_fields",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "tactical_matchup_diagnostic_run_id", "tactical_matchup_diagnostic_status",
    "rows_diagnosed", "tactical_evidence_status", "set_piece_xg_ratio_gate_status",
    "tactical_matchup_score_gate_status", "fatigue_modifier_gate_status",
    "xg_zone_correction_gate_status", "formation_matchup_gate_status",
    "transition_matchup_gate_status", "no_bet_tactical_safety_status",
    "missing_tactical_fields_count", "output_path", "summary_path",
    "recommendation", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class TacticalMatchupDiagnosticConfig:
    tactical_set_piece_fatigue_input_path: str | Path | None = None
    v19_diagnostic_gate_matrix_path: str | Path | None = None
    v19_diagnostic_synthesis_path: str | Path | None = None
    cross_provider_match_key: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/tactical_matchup_diagnostic"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class TacticalMatchupDiagnosticResult:
    tactical_matchup_diagnostic_run_id: str
    tactical_matchup_diagnostic_status: str
    rows_diagnosed: int
    tactical_evidence_status: str
    set_piece_xg_ratio_gate_status: str
    tactical_matchup_score_gate_status: str
    fatigue_modifier_gate_status: str
    xg_zone_correction_gate_status: str
    formation_matchup_gate_status: str
    transition_matchup_gate_status: str
    no_bet_tactical_safety_status: str
    missing_tactical_fields_count: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class TacticalMatchupDiagnosticRunner:
    def __init__(self, config: TacticalMatchupDiagnosticConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> TacticalMatchupDiagnosticResult:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.tactical_set_piece_fatigue_input_path, self.base)
        if out is None or (self.config.tactical_set_piece_fatigue_input_path is not None and _unsafe(self.config.tactical_set_piece_fatigue_input_path)) or (source is not None and _unsafe(source)):
            return self._blocked(TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_UNSAFE_PATH)
        if source is None or not source.exists():
            from scripts.build_tactical_set_piece_fatigue_input_preview import build_tactical_set_piece_fatigue_input_preview

            tactical = build_tactical_set_piece_fatigue_input_preview(
                cross_provider_match_key=self.config.cross_provider_match_key or "u-bundesliga-2024-001",
                output_dir=self.base / "outputs" / "analysis_preview" / "tactical_set_piece_fatigue_input",
                base_dir=self.base,
            )
            if tactical.get("tactical_set_piece_fatigue_input_status") != TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY:
                return self._blocked(TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_MISSING_TACTICAL_INPUT)
            source = Path(str(tactical.get("output_path", "")))
        try:
            frame = pd.read_csv(source, low_memory=False)
        except EmptyDataError:
            return self._blocked(TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_MISSING_TACTICAL_INPUT)
        selected = _select(frame, self.config.cross_provider_match_key)
        if selected.empty:
            return self._blocked(TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(TACTICAL_MATCHUP_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH)
        diagnostic = _diagnostic_row(selected.iloc[0])
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "tactical_matchup_diagnostic.csv"
        summary_path = out / "tactical_matchup_diagnostic_summary.md"
        manifest_path = out / "tactical_matchup_diagnostic_manifest.csv"
        pd.DataFrame([diagnostic], columns=OUTPUT_COLUMNS).to_csv(output_path, index=False)
        result = TacticalMatchupDiagnosticResult(
            "tactical_matchup_diagnostic_preview", TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY, 1,
            str(diagnostic["tactical_evidence_status"]),
            str(diagnostic["set_piece_xg_ratio_gate_status"]),
            str(diagnostic["tactical_matchup_score_gate_status"]),
            str(diagnostic["fatigue_modifier_gate_status"]),
            str(diagnostic["xg_zone_correction_gate_status"]),
            str(diagnostic["formation_matchup_gate_status"]),
            str(diagnostic["transition_matchup_gate_status"]),
            str(diagnostic["no_bet_tactical_safety_status"]),
            int(diagnostic["missing_tactical_fields_count"]), str(output_path.resolve()),
            str(summary_path.resolve()), str(manifest_path.resolve()),
            TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY, False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Tactical Matchup Diagnostic Preview", "",
            f"- tactical_matchup_diagnostic_status: {result.tactical_matchup_diagnostic_status}",
            f"- tactical_evidence_status: {result.tactical_evidence_status}",
            f"- set_piece_xg_ratio_gate_status: {result.set_piece_xg_ratio_gate_status}",
            f"- tactical_matchup_score_gate_status: {result.tactical_matchup_score_gate_status}",
            "- diagnostic-only tactical evidence; missing values are surfaced, not filled",
            "- no production prediction, betting output, position sizing, or financial return tracking", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str) -> TacticalMatchupDiagnosticResult:
        return TacticalMatchupDiagnosticResult(
            "tactical_matchup_diagnostic_preview", status, 0, "", "", "", "", "", "", "", "",
            0, "", "", "", status, False, False, False, False, False,
        )


def _diagnostic_row(row: pd.Series) -> dict[str, object]:
    missing_count = int(float(row.get("missing_tactical_fields_count", 0) or 0))
    evidence = "DIAGNOSTIC_READY" if missing_count == 0 else "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS"
    return {
        "match_date": row.get("match_date", ""), "competition": row.get("competition", ""),
        "season": row.get("season", ""), "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""), "cross_provider_match_key": row.get("cross_provider_match_key", ""),
        "tactical_evidence_status": evidence,
        "set_piece_xg_ratio_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_set_piece_xg_ratio", "away_set_piece_xg_ratio"]) else "DIAGNOSTIC_GATE_REQUIRES_TACTICAL_DATA",
        "tactical_matchup_score_gate_status": "DIAGNOSTIC_READY" if not _blank(row.get("tactical_matchup_score", "")) else "DIAGNOSTIC_GATE_REQUIRES_TACTICAL_DATA",
        "fatigue_modifier_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_rest_days", "away_rest_days", "do_so_fatigue_modifier"]) else "DIAGNOSTIC_GATE_REQUIRES_TACTICAL_DATA",
        "xg_zone_correction_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["xg_zone_correction_flag", "xg_zone_correction_note"]) else "DIAGNOSTIC_GATE_REQUIRES_TACTICAL_DATA",
        "formation_matchup_gate_status": "DIAGNOSTIC_READY" if not _blank(row.get("formation_matchup_note", "")) else "DIAGNOSTIC_GATE_REQUIRES_TACTICAL_DATA",
        "transition_matchup_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["transition_matchup_note", "defensive_line_risk_note"]) else "DIAGNOSTIC_GATE_REQUIRES_TACTICAL_DATA",
        "no_bet_tactical_safety_status": "BETTING_OUTPUT_DISABLED_BY_DESIGN",
        "home_tactical_note": row.get("home_tactical_profile", ""),
        "away_tactical_note": row.get("away_tactical_profile", ""),
        "tactical_matchup_note": " | ".join(str(row.get(c, "")) for c in ["formation_matchup_note", "pressing_matchup_note", "transition_matchup_note"] if not _blank(row.get(c, ""))),
        "missing_tactical_fields_count": missing_count,
        "missing_tactical_fields": row.get("missing_tactical_fields", ""),
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
    allowed = (base / "outputs" / "analysis_preview" / "tactical_matchup_diagnostic").resolve()
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
