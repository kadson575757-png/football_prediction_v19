# -*- coding: utf-8 -*-
"""Preview-only real match intake schema template builder."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REAL_MATCH_INTAKE_SCHEMA_PREVIEW_READY = "REAL_MATCH_INTAKE_SCHEMA_PREVIEW_READY"
REAL_MATCH_INTAKE_SCHEMA_BLOCKED_UNSAFE_PATH = "REAL_MATCH_INTAKE_SCHEMA_BLOCKED_UNSAFE_PATH"

IDENTITY_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team", "neutral_venue",
    "venue_name", "country", "timezone", "cross_provider_match_key",
    "understat_provider_match_id", "fbref_provider_match_id", "sofascore_provider_match_id",
    "fotmob_provider_match_id",
]
XG_COLUMNS = [
    "home_team_xg_for", "home_team_xg_against", "away_team_xg_for", "away_team_xg_against",
    "home_venue_xg_for", "home_venue_xg_against", "away_venue_xg_for", "away_venue_xg_against",
    "home_recent_xg_for", "home_recent_xg_against", "away_recent_xg_for",
    "away_recent_xg_against", "xg_source_note", "xg_data_quality_status",
]
MARKET_COLUMNS = [
    "home_open_odds", "draw_open_odds", "away_open_odds", "home_current_odds",
    "draw_current_odds", "away_current_odds", "home_closing_odds", "draw_closing_odds",
    "away_closing_odds", "market_snapshot_timestamp", "market_source_note",
    "market_data_quality_status",
]
AVAILABILITY_COLUMNS = [
    "home_lineup_confirmed", "away_lineup_confirmed", "home_missing_players",
    "away_missing_players", "home_key_absences", "away_key_absences",
    "home_goalkeeper_status", "away_goalkeeper_status", "home_formation",
    "away_formation", "availability_source_note", "availability_data_quality_status",
]
PLAYER_COLUMNS = [
    "home_main_scorer", "away_main_scorer", "home_main_creator", "away_main_creator",
    "home_player_xg_total", "away_player_xg_total", "home_player_xa_total",
    "away_player_xa_total", "home_big_chances", "away_big_chances",
    "home_conversion_signal", "away_conversion_signal", "player_form_source_note",
    "player_form_data_quality_status",
]
TACTICAL_COLUMNS = [
    "home_set_piece_xg_for", "away_set_piece_xg_for", "home_set_piece_xg_against",
    "away_set_piece_xg_against", "home_set_piece_xg_ratio", "away_set_piece_xg_ratio",
    "tactical_matchup_score", "home_tactical_profile", "away_tactical_profile",
    "formation_matchup_note", "pressing_matchup_note", "transition_matchup_note",
    "defensive_line_risk_note", "home_rest_days", "away_rest_days",
    "home_travel_fatigue_note", "away_travel_fatigue_note", "do_so_fatigue_modifier",
    "xg_zone_correction_flag", "xg_zone_correction_note", "tactical_source_note",
    "tactical_data_quality_status",
]
SAFETY_COLUMNS = [
    "analyst_note", "evidence_quality_note", "missing_required_fields_count",
    "missing_optional_fields_count", "manual_review_required", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
INTAKE_COLUMNS = IDENTITY_COLUMNS + XG_COLUMNS + MARKET_COLUMNS + AVAILABILITY_COLUMNS + PLAYER_COLUMNS + TACTICAL_COLUMNS + SAFETY_COLUMNS
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class RealMatchIntakeSchemaConfig:
    output_dir: str | Path = "outputs/analysis_preview/real_match_intake_schema"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class RealMatchIntakeSchemaResult:
    real_match_intake_schema_run_id: str
    real_match_intake_schema_status: str
    columns_written: int
    rows_written: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class RealMatchIntakeSchemaBuilder:
    def __init__(self, config: RealMatchIntakeSchemaConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> RealMatchIntakeSchemaResult:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(REAL_MATCH_INTAKE_SCHEMA_BLOCKED_UNSAFE_PATH)
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "real_match_intake_template.csv"
        summary_path = out / "real_match_intake_schema_summary.md"
        manifest_path = out / "real_match_intake_schema_manifest.csv"
        pd.DataFrame([_sample_row()], columns=INTAKE_COLUMNS).to_csv(output_path, index=False)
        result = RealMatchIntakeSchemaResult(
            "real_match_intake_schema_preview", REAL_MATCH_INTAKE_SCHEMA_PREVIEW_READY,
            len(INTAKE_COLUMNS), 1, str(output_path.resolve()), str(summary_path.resolve()),
            str(manifest_path.resolve()), REAL_MATCH_INTAKE_SCHEMA_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Real Match Intake Schema Preview", "",
            f"- real_match_intake_schema_status: {result.real_match_intake_schema_status}",
            f"- columns_written: {result.columns_written}",
            "- preview-only real-match intake template; no values are inferred",
            "- no production prediction, betting output, position sizing, or financial return tracking", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str) -> RealMatchIntakeSchemaResult:
        return RealMatchIntakeSchemaResult("real_match_intake_schema_preview", status, 0, 0, "", "", "", status, False, False, False, False, False)


def _sample_row() -> dict[str, object]:
    row = {column: "" for column in INTAKE_COLUMNS}
    row.update({
        "match_date": "2024-08-24", "competition": "Bundesliga", "season": "2024",
        "home_team": "Bayer Leverkusen", "away_team": "RB Leipzig",
        "neutral_venue": "false", "venue_name": "BayArena", "country": "Germany",
        "timezone": "Europe/Berlin", "cross_provider_match_key": "manual-bundesliga-2024-bayer-leverkusen-rb-leipzig-2024-08-24",
        "understat_provider_match_id": "manual-understat-bundesliga-2024-001",
        "fbref_provider_match_id": "manual-fbref-bundesliga-2024-001",
        "home_team_xg_for": 1.92, "home_team_xg_against": 0.98,
        "away_team_xg_for": 1.41, "away_team_xg_against": 1.26,
        "home_recent_xg_for": 9.8, "home_recent_xg_against": 5.2,
        "away_recent_xg_for": 7.1, "away_recent_xg_against": 7.9,
        "xg_source_note": "manual analyst intake", "xg_data_quality_status": "MANUAL_REVIEW_READY",
        "home_open_odds": 2.10, "draw_open_odds": 3.40, "away_open_odds": 3.20,
        "home_current_odds": 1.95, "draw_current_odds": 3.50, "away_current_odds": 3.60,
        "home_closing_odds": 1.90, "draw_closing_odds": 3.55, "away_closing_odds": 3.80,
        "market_snapshot_timestamp": "2024-08-24T10:00:00Z", "market_source_note": "manual market intake",
        "market_data_quality_status": "MANUAL_REVIEW_READY",
        "home_lineup_confirmed": "PROJECTED", "away_lineup_confirmed": "PROJECTED",
        "home_missing_players": "none listed", "away_missing_players": "main scorer doubtful",
        "home_key_absences": 0, "away_key_absences": 1, "home_goalkeeper_status": "AVAILABLE",
        "away_goalkeeper_status": "AVAILABLE", "home_formation": "3-4-2-1", "away_formation": "4-2-3-1",
        "availability_source_note": "manual availability intake", "availability_data_quality_status": "MANUAL_REVIEW_READY",
        "home_main_scorer": "Home Striker", "away_main_scorer": "Away Forward",
        "home_main_creator": "Home Creator", "away_main_creator": "Away Creator",
        "home_player_xg_total": 0.62, "away_player_xg_total": 0.48,
        "home_player_xa_total": 0.31, "away_player_xa_total": 0.27,
        "home_big_chances": 9, "away_big_chances": 6,
        "home_conversion_signal": "slight overconversion", "away_conversion_signal": "near xG expectation",
        "player_form_source_note": "manual player/form intake", "player_form_data_quality_status": "MANUAL_REVIEW_READY",
        "home_set_piece_xg_for": 0.42, "away_set_piece_xg_for": 0.31,
        "home_set_piece_xg_against": 0.22, "away_set_piece_xg_against": 0.39,
        "home_set_piece_xg_ratio": 1.91, "away_set_piece_xg_ratio": 0.79,
        "tactical_matchup_score": 7.4, "home_tactical_profile": "possession press with strong rest-defense",
        "away_tactical_profile": "vertical transition side",
        "formation_matchup_note": "home overloads half-spaces against away back four",
        "pressing_matchup_note": "home press can disrupt first progression line",
        "transition_matchup_note": "away transition threat remains visible",
        "defensive_line_risk_note": "home high line requires depth control",
        "home_rest_days": 6, "away_rest_days": 4,
        "home_travel_fatigue_note": "normal rest and no travel concern",
        "away_travel_fatigue_note": "shorter rest after away travel",
        "do_so_fatigue_modifier": "mild_away_fatigue",
        "xg_zone_correction_flag": "ZONE_CORRECTION_REVIEW_READY",
        "xg_zone_correction_note": "central box volume supports xG read",
        "tactical_source_note": "manual tactical intake", "tactical_data_quality_status": "MANUAL_REVIEW_READY",
        "analyst_note": "manual real-match preview row", "evidence_quality_note": "diagnostic preview only",
        "missing_required_fields_count": 0, "missing_optional_fields_count": 0,
        "manual_review_required": "true", "network_calls_enabled": "false",
        "prediction_logic_enabled": "false", "betting_logic_enabled": "false",
        "staking_logic_enabled": "false", "roi_logic_enabled": "false",
    })
    return row


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "real_match_intake_schema").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None
