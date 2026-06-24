# -*- coding: utf-8 -*-
"""Preview-only manual evidence overlay for existing analysis layers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY = "MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY"
MANUAL_EVIDENCE_OVERLAY_BLOCKED_MISSING_VALID_INTAKE = "MANUAL_EVIDENCE_OVERLAY_BLOCKED_MISSING_VALID_INTAKE"
MANUAL_EVIDENCE_OVERLAY_BLOCKED_UNSAFE_PATH = "MANUAL_EVIDENCE_OVERLAY_BLOCKED_UNSAFE_PATH"
MANUAL_EVIDENCE_OVERLAY_NO_BETTING_OUTPUT_BY_DESIGN = "MANUAL_EVIDENCE_OVERLAY_NO_BETTING_OUTPUT_BY_DESIGN"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class ManualEvidenceOverlayConfig:
    input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/manual_evidence_overlay"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class ManualEvidenceOverlayResult:
    manual_evidence_overlay_run_id: str
    manual_evidence_overlay_status: str
    rows_overlayed: int
    market_overlay_status: str
    availability_overlay_status: str
    player_form_overlay_status: str
    tactical_overlay_status: str
    output_path: str
    summary_path: str
    manifest_path: str
    odds_overlay_path: str
    availability_overlay_path: str
    player_form_overlay_path: str
    tactical_overlay_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class ManualEvidenceOverlayBuilder:
    def __init__(self, config: ManualEvidenceOverlayConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> ManualEvidenceOverlayResult:
        source = _resolve(self.config.input_path, self.base)
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or source is None or _unsafe(source):
            return self._blocked(MANUAL_EVIDENCE_OVERLAY_BLOCKED_UNSAFE_PATH)
        try:
            frame = pd.read_csv(source, low_memory=False, keep_default_na=False)
        except (FileNotFoundError, EmptyDataError):
            return self._blocked(MANUAL_EVIDENCE_OVERLAY_BLOCKED_MISSING_VALID_INTAKE)
        if frame.empty or "real_match_intake_validation_status" not in frame.columns or str(frame.iloc[0].get("real_match_intake_validation_status", "")) != "REAL_MATCH_INTAKE_VALIDATION_READY":
            return self._blocked(MANUAL_EVIDENCE_OVERLAY_BLOCKED_MISSING_VALID_INTAKE)
        row = frame.iloc[0]
        out.mkdir(parents=True, exist_ok=True)
        overlay = _overlay_summary(row)
        odds = _odds(row)
        availability = _availability(row)
        player = _player(row)
        tactical = _tactical(row)
        output_path = out / "manual_evidence_overlay.csv"
        summary_path = out / "manual_evidence_overlay_summary.md"
        manifest_path = out / "manual_evidence_overlay_manifest.csv"
        odds_path = out / "odds_market_movement_input_overlay.csv"
        availability_path = out / "lineups_availability_input_overlay.csv"
        player_path = out / "player_impact_rolling_form_input_overlay.csv"
        tactical_path = out / "tactical_set_piece_fatigue_input_overlay.csv"
        pd.DataFrame([overlay]).to_csv(output_path, index=False)
        pd.DataFrame([odds]).to_csv(odds_path, index=False)
        pd.DataFrame([availability]).to_csv(availability_path, index=False)
        pd.DataFrame([player]).to_csv(player_path, index=False)
        pd.DataFrame([tactical]).to_csv(tactical_path, index=False)
        result = ManualEvidenceOverlayResult(
            "manual_evidence_overlay_preview", MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY, 1,
            overlay["market_overlay_status"], overlay["availability_overlay_status"],
            overlay["player_form_overlay_status"], overlay["tactical_overlay_status"],
            str(output_path.resolve()), str(summary_path.resolve()), str(manifest_path.resolve()),
            str(odds_path.resolve()), str(availability_path.resolve()), str(player_path.resolve()),
            str(tactical_path.resolve()), MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Manual Evidence Overlay Preview", "",
            f"- manual_evidence_overlay_status: {result.manual_evidence_overlay_status}",
            f"- rows_overlayed: {result.rows_overlayed}",
            f"- market_overlay_status: {result.market_overlay_status}",
            f"- availability_overlay_status: {result.availability_overlay_status}",
            f"- player_form_overlay_status: {result.player_form_overlay_status}",
            f"- tactical_overlay_status: {result.tactical_overlay_status}",
            "- missing optional evidence remains blank; no values are inferred",
            "- no production prediction, betting output, position sizing, or financial return tracking", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str) -> ManualEvidenceOverlayResult:
        return ManualEvidenceOverlayResult("manual_evidence_overlay_preview", status, 0, "", "", "", "", "", "", "", "", "", "", "", status, False, False, False, False, False)


def _identity(row: pd.Series) -> dict[str, object]:
    return {
        "match_date": row.get("match_date", ""), "competition": row.get("competition", ""),
        "season": row.get("season", ""), "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""), "understat_provider_match_id": row.get("understat_provider_match_id", ""),
        "fbref_provider_match_id": row.get("fbref_provider_match_id", ""),
        "cross_provider_match_key": row.get("cross_provider_match_key", ""),
    }


def _odds(row: pd.Series) -> dict[str, object]:
    data = _identity(row)
    data.update({
        "market_snapshot_source": _value(row, "market_source_note", "manual_evidence_overlay"),
        "market_snapshot_timestamp": _value(row, "market_snapshot_timestamp", "manual_preview_timestamp_missing"),
        "home_open_odds": row.get("home_open_odds", ""), "draw_open_odds": row.get("draw_open_odds", ""),
        "away_open_odds": row.get("away_open_odds", ""), "home_current_odds": row.get("home_current_odds", ""),
        "draw_current_odds": row.get("draw_current_odds", ""), "away_current_odds": row.get("away_current_odds", ""),
        "home_closing_odds": row.get("home_closing_odds", ""), "draw_closing_odds": row.get("draw_closing_odds", ""),
        "away_closing_odds": row.get("away_closing_odds", ""),
    })
    return data


def _availability(row: pd.Series) -> dict[str, object]:
    data = _identity(row)
    data.update({
        "availability_snapshot_source": _value(row, "availability_source_note", "manual_evidence_overlay"),
        "availability_snapshot_timestamp": _value(row, "market_snapshot_timestamp", "manual_preview_timestamp_missing"),
        "home_lineup_status": row.get("home_lineup_confirmed", ""),
        "away_lineup_status": row.get("away_lineup_confirmed", ""),
        "home_formation": row.get("home_formation", ""), "away_formation": row.get("away_formation", ""),
        "home_goalkeeper_status": row.get("home_goalkeeper_status", ""),
        "away_goalkeeper_status": row.get("away_goalkeeper_status", ""),
        "home_defensive_line_status": "", "away_defensive_line_status": "",
        "home_main_scorer_status": "AVAILABLE" if not _blank(row.get("home_main_scorer", "")) else "",
        "away_main_scorer_status": "AVAILABLE" if not _blank(row.get("away_main_scorer", "")) else "",
        "home_missing_players": row.get("home_missing_players", ""),
        "away_missing_players": row.get("away_missing_players", ""),
        "home_suspended_players": "", "away_suspended_players": "",
        "home_doubtful_players": "", "away_doubtful_players": "",
        "home_key_absence_count": row.get("home_key_absences", ""),
        "away_key_absence_count": row.get("away_key_absences", ""),
    })
    return data


def _player(row: pd.Series) -> dict[str, object]:
    data = _identity(row)
    data.update({
        "player_form_snapshot_source": _value(row, "player_form_source_note", "manual_evidence_overlay"),
        "player_form_snapshot_timestamp": _value(row, "market_snapshot_timestamp", "manual_preview_timestamp_missing"),
        "home_top_xg_player": row.get("home_main_scorer", ""), "away_top_xg_player": row.get("away_main_scorer", ""),
        "home_top_xg_value": row.get("home_player_xg_total", ""), "away_top_xg_value": row.get("away_player_xg_total", ""),
        "home_top_xa_player": row.get("home_main_creator", ""), "away_top_xa_player": row.get("away_main_creator", ""),
        "home_top_xa_value": row.get("home_player_xa_total", ""), "away_top_xa_value": row.get("away_player_xa_total", ""),
        "home_big_chances_for": row.get("home_big_chances", ""), "away_big_chances_for": row.get("away_big_chances", ""),
        "home_big_chances_against": "", "away_big_chances_against": "",
        "home_recent_matches": "", "away_recent_matches": "",
        "home_recent_goals_for": "", "away_recent_goals_for": "",
        "home_recent_goals_against": "", "away_recent_goals_against": "",
        "home_recent_xg_for": row.get("home_recent_xg_for", ""), "away_recent_xg_for": row.get("away_recent_xg_for", ""),
        "home_recent_xg_against": row.get("home_recent_xg_against", ""), "away_recent_xg_against": row.get("away_recent_xg_against", ""),
        "home_recent_conversion_note": row.get("home_conversion_signal", ""),
        "away_recent_conversion_note": row.get("away_conversion_signal", ""),
        "home_main_creator_status": "AVAILABLE" if not _blank(row.get("home_main_creator", "")) else "",
        "away_main_creator_status": "AVAILABLE" if not _blank(row.get("away_main_creator", "")) else "",
        "home_main_scorer_status": "AVAILABLE" if not _blank(row.get("home_main_scorer", "")) else "",
        "away_main_scorer_status": "AVAILABLE" if not _blank(row.get("away_main_scorer", "")) else "",
        "home_player_impact_note": row.get("player_form_source_note", ""),
        "away_player_impact_note": row.get("player_form_source_note", ""),
    })
    return data


def _tactical(row: pd.Series) -> dict[str, object]:
    data = _identity(row)
    data.update({
        "tactical_snapshot_source": _value(row, "tactical_source_note", "manual_evidence_overlay"),
        "tactical_snapshot_timestamp": _value(row, "market_snapshot_timestamp", "manual_preview_timestamp_missing"),
    })
    for column in [
        "home_set_piece_xg_for", "away_set_piece_xg_for", "home_set_piece_xg_against",
        "away_set_piece_xg_against", "home_set_piece_xg_ratio", "away_set_piece_xg_ratio",
        "tactical_matchup_score", "home_tactical_profile", "away_tactical_profile",
        "formation_matchup_note", "pressing_matchup_note", "transition_matchup_note",
        "defensive_line_risk_note", "home_rest_days", "away_rest_days",
        "home_travel_fatigue_note", "away_travel_fatigue_note", "do_so_fatigue_modifier",
        "xg_zone_correction_flag", "xg_zone_correction_note",
    ]:
        data[column] = row.get(column, "")
    return data


def _overlay_summary(row: pd.Series) -> dict[str, object]:
    return {
        **_identity(row),
        "manual_evidence_overlay_status": MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY,
        "market_overlay_status": _status(_odds(row), ["home_closing_odds", "draw_closing_odds", "away_closing_odds"]),
        "availability_overlay_status": _status(_availability(row), ["home_defensive_line_status", "away_defensive_line_status"]),
        "player_form_overlay_status": _status(_player(row), ["home_recent_matches", "away_recent_matches", "home_big_chances_against", "away_big_chances_against"]),
        "tactical_overlay_status": _status(_tactical(row), ["xg_zone_correction_note"]),
        "network_calls_enabled": False, "prediction_logic_enabled": False,
        "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
    }


def _status(data: dict[str, object], optional: list[str]) -> str:
    return "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS" if any(_blank(data.get(c, "")) for c in optional) else "DIAGNOSTIC_READY"


def _value(row: pd.Series, column: str, fallback: object) -> object:
    value = row.get(column, "")
    return fallback if _blank(value) else value


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "manual_evidence_overlay").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""
