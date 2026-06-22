# -*- coding: utf-8 -*-
"""Preview-only availability diagnostic layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from football_prediction_v19.analysis.lineups_availability_input_preview import LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY

AVAILABILITY_DIAGNOSTIC_PREVIEW_READY = "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
AVAILABILITY_DIAGNOSTIC_BLOCKED_MISSING_AVAILABILITY_INPUT = "AVAILABILITY_DIAGNOSTIC_BLOCKED_MISSING_AVAILABILITY_INPUT"
AVAILABILITY_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH = "AVAILABILITY_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH"
AVAILABILITY_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH = "AVAILABILITY_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH"
AVAILABILITY_DIAGNOSTIC_BLOCKED_UNSAFE_PATH = "AVAILABILITY_DIAGNOSTIC_BLOCKED_UNSAFE_PATH"
AVAILABILITY_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN = "AVAILABILITY_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN"
AVAILABILITY_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN = "AVAILABILITY_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN"

OUTPUT_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team", "cross_provider_match_key",
    "availability_evidence_status", "lineup_confirmation_gate_status",
    "injuries_suspensions_gate_status", "formation_availability_gate_status",
    "goalkeeper_availability_gate_status", "key_absence_gate_status",
    "no_bet_availability_safety_status", "home_availability_note",
    "away_availability_note", "missing_availability_fields_count",
    "missing_availability_fields", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "availability_diagnostic_run_id", "availability_diagnostic_status",
    "rows_diagnosed", "availability_evidence_status", "lineup_confirmation_gate_status",
    "injuries_suspensions_gate_status", "formation_availability_gate_status",
    "goalkeeper_availability_gate_status", "key_absence_gate_status",
    "no_bet_availability_safety_status", "missing_availability_fields_count",
    "output_path", "summary_path", "recommendation", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class AvailabilityDiagnosticConfig:
    lineups_availability_input_path: str | Path | None = None
    v19_diagnostic_gate_matrix_path: str | Path | None = None
    v19_diagnostic_synthesis_path: str | Path | None = None
    cross_provider_match_key: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/availability_diagnostic"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class AvailabilityDiagnosticResult:
    availability_diagnostic_run_id: str
    availability_diagnostic_status: str
    rows_diagnosed: int
    availability_evidence_status: str
    lineup_confirmation_gate_status: str
    injuries_suspensions_gate_status: str
    formation_availability_gate_status: str
    goalkeeper_availability_gate_status: str
    key_absence_gate_status: str
    no_bet_availability_safety_status: str
    missing_availability_fields_count: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class AvailabilityDiagnosticRunner:
    def __init__(self, config: AvailabilityDiagnosticConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> AvailabilityDiagnosticResult:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.lineups_availability_input_path, self.base)
        if out is None or (self.config.lineups_availability_input_path is not None and _unsafe(self.config.lineups_availability_input_path)) or (source is not None and _unsafe(source)):
            return self._blocked(AVAILABILITY_DIAGNOSTIC_BLOCKED_UNSAFE_PATH)
        if source is None or not source.exists():
            from scripts.build_lineups_availability_input_preview import build_lineups_availability_input_preview

            availability = build_lineups_availability_input_preview(
                cross_provider_match_key=self.config.cross_provider_match_key or "u-bundesliga-2024-001",
                output_dir=self.base / "outputs" / "analysis_preview" / "lineups_availability_input",
                base_dir=self.base,
            )
            if availability.get("lineups_availability_input_status") != LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY:
                return self._blocked(AVAILABILITY_DIAGNOSTIC_BLOCKED_MISSING_AVAILABILITY_INPUT)
            source = Path(str(availability.get("output_path", "")))
        try:
            frame = pd.read_csv(source, low_memory=False)
        except EmptyDataError:
            return self._blocked(AVAILABILITY_DIAGNOSTIC_BLOCKED_MISSING_AVAILABILITY_INPUT)
        selected = _select(frame, self.config.cross_provider_match_key)
        if selected.empty:
            return self._blocked(AVAILABILITY_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(AVAILABILITY_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH)
        diagnostic = _diagnostic_row(selected.iloc[0])
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "availability_diagnostic.csv"
        summary_path = out / "availability_diagnostic_summary.md"
        manifest_path = out / "availability_diagnostic_manifest.csv"
        pd.DataFrame([diagnostic], columns=OUTPUT_COLUMNS).to_csv(output_path, index=False)
        result = AvailabilityDiagnosticResult(
            "availability_diagnostic_preview", AVAILABILITY_DIAGNOSTIC_PREVIEW_READY, 1,
            str(diagnostic["availability_evidence_status"]), str(diagnostic["lineup_confirmation_gate_status"]),
            str(diagnostic["injuries_suspensions_gate_status"]), str(diagnostic["formation_availability_gate_status"]),
            str(diagnostic["goalkeeper_availability_gate_status"]), str(diagnostic["key_absence_gate_status"]),
            str(diagnostic["no_bet_availability_safety_status"]), int(diagnostic["missing_availability_fields_count"]),
            str(output_path.resolve()), str(summary_path.resolve()), str(manifest_path.resolve()),
            AVAILABILITY_DIAGNOSTIC_PREVIEW_READY, False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(
            "\n".join([
                "# Availability Diagnostic Preview", "",
                f"- availability_diagnostic_status: {result.availability_diagnostic_status}",
                f"- availability_evidence_status: {result.availability_evidence_status}",
                f"- lineup_confirmation_gate_status: {result.lineup_confirmation_gate_status}",
                f"- injuries_suspensions_gate_status: {result.injuries_suspensions_gate_status}",
                "- diagnostic-only availability evidence; missing player values are surfaced, not filled",
                "- no production prediction, betting output, position sizing, or financial return tracking",
                "",
            ]),
            encoding="utf-8",
        )
        return result

    def _blocked(self, status: str) -> AvailabilityDiagnosticResult:
        return AvailabilityDiagnosticResult(
            "availability_diagnostic_preview", status, 0, "", "", "", "", "", "", "",
            0, "", "", "", status, False, False, False, False, False,
        )


def _diagnostic_row(row: pd.Series) -> dict[str, object]:
    missing_count = int(float(row.get("missing_availability_fields_count", 0) or 0))
    evidence = "DIAGNOSTIC_READY" if missing_count == 0 else "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS"
    return {
        "match_date": row.get("match_date", ""), "competition": row.get("competition", ""),
        "season": row.get("season", ""), "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""), "cross_provider_match_key": row.get("cross_provider_match_key", ""),
        "availability_evidence_status": evidence,
        "lineup_confirmation_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_lineup_status", "away_lineup_status"]) else "DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA",
        "injuries_suspensions_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_missing_players", "away_missing_players", "home_suspended_players", "away_suspended_players"]) else "DIAGNOSTIC_GATE_REQUIRES_AVAILABILITY_DATA",
        "formation_availability_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_formation", "away_formation"]) else "DIAGNOSTIC_GATE_REQUIRES_AVAILABILITY_DATA",
        "goalkeeper_availability_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_goalkeeper_status", "away_goalkeeper_status"]) else "DIAGNOSTIC_GATE_REQUIRES_AVAILABILITY_DATA",
        "key_absence_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_key_absence_count", "away_key_absence_count"]) else "DIAGNOSTIC_GATE_REQUIRES_AVAILABILITY_DATA",
        "no_bet_availability_safety_status": "BETTING_OUTPUT_DISABLED_BY_DESIGN",
        "home_availability_note": f"Lineup={row.get('home_lineup_status', '')}; keeper={row.get('home_goalkeeper_status', '')}; key_absences={row.get('home_key_absence_count', '')}",
        "away_availability_note": f"Lineup={row.get('away_lineup_status', '')}; keeper={row.get('away_goalkeeper_status', '')}; key_absences={row.get('away_key_absence_count', '')}",
        "missing_availability_fields_count": missing_count,
        "missing_availability_fields": row.get("missing_availability_fields", ""),
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
    allowed = (base / "outputs" / "analysis_preview" / "availability_diagnostic").resolve()
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
