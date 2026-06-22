# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.availability_diagnostic_preview import AvailabilityDiagnosticConfig, AvailabilityDiagnosticRunner
from football_prediction_v19.analysis.lineups_availability_input_preview import LineupsAvailabilityInputConfig, LineupsAvailabilityInputRunner
from scripts.audit_availability_diagnostic_24_block_preview import audit_availability_diagnostic_24_block_preview
from scripts.build_availability_diagnostic_24_block_preview_helper import build_availability_diagnostic_24_block_preview_helper
from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview
from scripts.run_match_analysis_preview import run_match_analysis_preview


def test_availability_input_builds_deterministic_fixture() -> None:
    result = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig(cross_provider_match_key="u-bundesliga-2024-001")).run()
    assert result.lineups_availability_input_status == "LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY"
    assert result.rows_written == 1
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["cross_provider_match_key"] == "u-bundesliga-2024-001"
    assert str(row["network_calls_enabled"]).lower() == "false"


def test_availability_input_csv_unknown_ambiguous_and_missing_columns(tmp_path: Path) -> None:
    base = pd.read_csv(LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig()).run().output_path)
    path = tmp_path / "availability.csv"
    pd.concat([base, base.assign(cross_provider_match_key="u-bundesliga-2024-002", home_team="Other")]).to_csv(path, index=False)
    ready = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig(cross_provider_match_key="u-bundesliga-2024-001", availability_input_path=path)).run()
    assert ready.lineups_availability_input_status == "LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY"
    unknown = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig(cross_provider_match_key="missing", availability_input_path=path)).run()
    assert unknown.lineups_availability_input_status == "LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNKNOWN_MATCH"
    ambiguous = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig(competition="Bundesliga", availability_input_path=path)).run()
    assert ambiguous.lineups_availability_input_status == "LINEUPS_AVAILABILITY_INPUT_BLOCKED_AMBIGUOUS_MATCH"
    bad = tmp_path / "bad.csv"
    base.drop(columns=["availability_snapshot_source"]).to_csv(bad, index=False)
    missing = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig(availability_input_path=bad)).run()
    assert missing.lineups_availability_input_status == "LINEUPS_AVAILABILITY_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"


def test_availability_input_blocks_unsafe_and_surfaces_missing_optional(tmp_path: Path) -> None:
    unsafe = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig(availability_input_path="https://example.test/availability.csv")).run()
    assert unsafe.lineups_availability_input_status == "LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNSAFE_PATH"
    frame = pd.read_csv(LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig()).run().output_path)
    frame.loc[0, "away_doubtful_players"] = ""
    path = tmp_path / "missing_optional.csv"
    frame.to_csv(path, index=False)
    result = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig(availability_input_path=path)).run()
    row = pd.read_csv(result.output_path).iloc[0]
    assert int(row["missing_availability_fields_count"]) >= 1
    assert "away_doubtful_players" in str(row["missing_availability_fields"])


def test_availability_diagnostic_sets_gate_statuses_and_leaves_missing_values_missing(tmp_path: Path) -> None:
    input_result = LineupsAvailabilityInputRunner(LineupsAvailabilityInputConfig()).run()
    result = AvailabilityDiagnosticRunner(AvailabilityDiagnosticConfig(lineups_availability_input_path=input_result.output_path)).run()
    assert result.availability_diagnostic_status == "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["lineup_confirmation_gate_status"] == "DIAGNOSTIC_READY"
    assert row["injuries_suspensions_gate_status"] == "DIAGNOSTIC_READY"
    assert row["formation_availability_gate_status"] == "DIAGNOSTIC_READY"
    assert row["key_absence_gate_status"] == "DIAGNOSTIC_READY"
    assert row["no_bet_availability_safety_status"] == "BETTING_OUTPUT_DISABLED_BY_DESIGN"
    frame = pd.read_csv(input_result.output_path)
    frame.loc[0, "home_formation"] = ""
    missing_path = tmp_path / "missing_formation.csv"
    frame.to_csv(missing_path, index=False)
    missing = AvailabilityDiagnosticRunner(AvailabilityDiagnosticConfig(lineups_availability_input_path=missing_path)).run()
    missing_row = pd.read_csv(missing.output_path).iloc[0]
    assert missing_row["formation_availability_gate_status"] == "DIAGNOSTIC_GATE_REQUIRES_AVAILABILITY_DATA"


def test_pipeline_bundle_excel_helper_and_audit_include_availability_layer() -> None:
    command = run_match_analysis_preview(cross_provider_match_key="u-bundesliga-2024-001")
    assert command["command_status"] == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"
    assert command["odds_market_movement_input_status"] == "ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY"
    assert command["market_movement_diagnostic_status"] == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    assert command["lineups_availability_input_status"] == "LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY"
    assert command["availability_diagnostic_status"] == "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
    assert int(command["sheets_written"]) >= 12
    report = Path(str(command["human_report_path"])).read_text(encoding="utf-8")
    assert "Availability diagnostic status" in report
    bundle = build_match_analysis_export_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001")
    bundle_dir = Path(str(bundle["export_bundle_dir"]))
    assert (bundle_dir / "lineups_availability_input_review.csv").exists()
    assert (bundle_dir / "availability_diagnostic_review.csv").exists()
    helper = build_availability_diagnostic_24_block_preview_helper()
    assert helper["recommendation"] == "AVAILABILITY_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
    audit = audit_availability_diagnostic_24_block_preview()
    assert audit["recommendation"] == "AVAILABILITY_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
