# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.real_match_intake_schema_preview import INTAKE_COLUMNS, RealMatchIntakeSchemaBuilder, RealMatchIntakeSchemaConfig
from football_prediction_v19.analysis.real_match_intake_validation_preview import RealMatchIntakeValidationConfig, RealMatchIntakeValidator
from football_prediction_v19.analysis.manual_evidence_overlay_preview import ManualEvidenceOverlayBuilder, ManualEvidenceOverlayConfig
from scripts.audit_real_match_input_pack_preview import audit_real_match_input_pack_preview
from scripts.build_real_match_input_pack_preview import build_real_match_input_pack_preview
from scripts.run_match_analysis_preview import run_match_analysis_preview


def test_schema_builder_creates_template_with_required_columns() -> None:
    result = RealMatchIntakeSchemaBuilder(RealMatchIntakeSchemaConfig()).run()
    assert result.real_match_intake_schema_status == "REAL_MATCH_INTAKE_SCHEMA_PREVIEW_READY"
    assert result.columns_written >= 90
    frame = pd.read_csv(result.output_path)
    for column in ["match_date", "competition", "home_team", "away_team", "home_current_odds", "home_set_piece_xg_ratio"]:
        assert column in frame.columns
    assert set(INTAKE_COLUMNS).issubset(set(frame.columns))


def test_validation_accepts_row_and_generates_manual_key(tmp_path: Path) -> None:
    schema = RealMatchIntakeSchemaBuilder(RealMatchIntakeSchemaConfig()).run()
    ready = RealMatchIntakeValidator(RealMatchIntakeValidationConfig(input_path=schema.output_path)).run()
    assert ready.real_match_intake_validation_status == "REAL_MATCH_INTAKE_VALIDATION_READY"
    frame = pd.read_csv(schema.output_path)
    frame.loc[0, "cross_provider_match_key"] = ""
    path = tmp_path / "manual_key.csv"
    frame.to_csv(path, index=False)
    generated = RealMatchIntakeValidator(RealMatchIntakeValidationConfig(input_path=path, manual_key_generation_enabled=True)).run()
    assert generated.real_match_intake_validation_status == "REAL_MATCH_INTAKE_VALIDATION_READY"
    row = pd.read_csv(generated.output_path).iloc[0]
    assert str(row["cross_provider_match_key"]).startswith("manual-bundesliga-2024")


def test_validation_blocks_missing_empty_duplicate_and_unsafe(tmp_path: Path) -> None:
    schema = RealMatchIntakeSchemaBuilder(RealMatchIntakeSchemaConfig()).run()
    frame = pd.read_csv(schema.output_path)
    missing_path = tmp_path / "missing.csv"
    frame.drop(columns=["home_team"]).to_csv(missing_path, index=False)
    missing = RealMatchIntakeValidator(RealMatchIntakeValidationConfig(input_path=missing_path)).run()
    assert missing.real_match_intake_validation_status == "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_MISSING_REQUIRED_COLUMNS"
    empty_path = tmp_path / "empty.csv"
    frame.assign(home_team="").to_csv(empty_path, index=False)
    empty = RealMatchIntakeValidator(RealMatchIntakeValidationConfig(input_path=empty_path)).run()
    assert empty.real_match_intake_validation_status == "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_EMPTY_REQUIRED_VALUES"
    duplicate_path = tmp_path / "dup.csv"
    pd.concat([frame, frame]).to_csv(duplicate_path, index=False)
    duplicate = RealMatchIntakeValidator(RealMatchIntakeValidationConfig(input_path=duplicate_path)).run()
    assert duplicate.real_match_intake_validation_status == "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_DUPLICATE_MATCHES"
    unsafe = RealMatchIntakeValidator(RealMatchIntakeValidationConfig(input_path="https://example.test/intake.csv")).run()
    assert unsafe.real_match_intake_validation_status == "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_UNSAFE_PATH"


def test_overlay_builds_split_files_and_surfaces_missing_optional(tmp_path: Path) -> None:
    schema = RealMatchIntakeSchemaBuilder(RealMatchIntakeSchemaConfig()).run()
    frame = pd.read_csv(schema.output_path)
    frame["away_closing_odds"] = frame["away_closing_odds"].astype(object)
    frame.loc[0, "away_closing_odds"] = ""
    intake = tmp_path / "intake.csv"
    frame.to_csv(intake, index=False)
    validation = RealMatchIntakeValidator(RealMatchIntakeValidationConfig(input_path=intake)).run()
    result = ManualEvidenceOverlayBuilder(ManualEvidenceOverlayConfig(input_path=validation.output_path)).run()
    assert result.manual_evidence_overlay_status == "MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY"
    assert Path(result.odds_overlay_path).exists()
    assert Path(result.availability_overlay_path).exists()
    assert Path(result.player_form_overlay_path).exists()
    assert Path(result.tactical_overlay_path).exists()
    overlay = pd.read_csv(result.output_path).iloc[0]
    assert overlay["market_overlay_status"] == "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS"
    odds = pd.read_csv(result.odds_overlay_path).iloc[0]
    assert pd.isna(odds["away_closing_odds"]) or str(odds["away_closing_odds"]).strip() == ""


def test_real_match_input_pack_and_run_command_with_intake() -> None:
    pack = build_real_match_input_pack_preview()
    assert pack["real_match_input_pack_status"] == "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
    assert pack["manual_evidence_overlay_status"] == "MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY"
    assert pack["market_movement_diagnostic_status"] == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    assert pack["availability_diagnostic_status"] == "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
    assert pack["player_form_diagnostic_status"] == "PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY"
    assert pack["tactical_matchup_diagnostic_status"] == "TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY"
    assert int(pack["sheets_written"]) >= 16
    assert int(pack["exported_files_count"]) >= 14
    assert int(pack["sections_rendered"]) == 24
    assert not any(bool(pack[k]) for k in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"])
    command = run_match_analysis_preview(real_match_intake="outputs/analysis_preview/real_match_intake_schema/real_match_intake_template.csv")
    assert command["real_match_input_pack_status"] == "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
    deterministic = run_match_analysis_preview(cross_provider_match_key="u-bundesliga-2024-001")
    assert deterministic["command_status"] == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"
    audit = audit_real_match_input_pack_preview()
    assert audit["recommendation"] == "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
