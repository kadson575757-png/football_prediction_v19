# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.player_form_diagnostic_preview import PlayerFormDiagnosticConfig, PlayerFormDiagnosticRunner
from football_prediction_v19.analysis.player_impact_rolling_form_input_preview import PlayerImpactRollingFormInputConfig, PlayerImpactRollingFormInputRunner
from scripts.audit_player_form_diagnostic_24_block_preview import audit_player_form_diagnostic_24_block_preview
from scripts.build_player_form_diagnostic_24_block_preview_helper import build_player_form_diagnostic_24_block_preview_helper
from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview
from scripts.run_match_analysis_preview import run_match_analysis_preview


def test_player_form_input_builds_deterministic_fixture() -> None:
    result = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(cross_provider_match_key="u-bundesliga-2024-001")).run()
    assert result.player_impact_rolling_form_input_status == "PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY"
    assert result.rows_written == 1
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["cross_provider_match_key"] == "u-bundesliga-2024-001"
    assert str(row["network_calls_enabled"]).lower() == "false"


def test_player_form_input_csv_unknown_ambiguous_and_missing_columns(tmp_path: Path) -> None:
    base = pd.read_csv(PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig()).run().output_path)
    path = tmp_path / "player_form.csv"
    pd.concat([base, base.assign(cross_provider_match_key="u-bundesliga-2024-002", home_team="Other")]).to_csv(path, index=False)
    ready = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(cross_provider_match_key="u-bundesliga-2024-001", player_form_input_path=path)).run()
    assert ready.player_impact_rolling_form_input_status == "PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY"
    unknown = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(cross_provider_match_key="missing", player_form_input_path=path)).run()
    assert unknown.player_impact_rolling_form_input_status == "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNKNOWN_MATCH"
    ambiguous = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(competition="Bundesliga", player_form_input_path=path)).run()
    assert ambiguous.player_impact_rolling_form_input_status == "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_AMBIGUOUS_MATCH"
    bad = tmp_path / "bad.csv"
    base.drop(columns=["player_form_snapshot_source"]).to_csv(bad, index=False)
    missing = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(player_form_input_path=bad)).run()
    assert missing.player_impact_rolling_form_input_status == "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"


def test_player_form_input_blocks_unsafe_and_surfaces_missing_optional(tmp_path: Path) -> None:
    unsafe = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(player_form_input_path="https://example.test/player_form.csv")).run()
    assert unsafe.player_impact_rolling_form_input_status == "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNSAFE_PATH"
    frame = pd.read_csv(PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig()).run().output_path)
    frame.loc[0, "away_recent_conversion_note"] = ""
    path = tmp_path / "missing_optional.csv"
    frame.to_csv(path, index=False)
    result = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(player_form_input_path=path)).run()
    row = pd.read_csv(result.output_path).iloc[0]
    assert int(row["missing_player_form_fields_count"]) >= 1
    assert "away_recent_conversion_note" in str(row["missing_player_form_fields"])


def test_player_form_diagnostic_sets_gate_statuses_and_leaves_missing_values_missing(tmp_path: Path) -> None:
    input_result = PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig()).run()
    result = PlayerFormDiagnosticRunner(PlayerFormDiagnosticConfig(player_impact_rolling_form_input_path=input_result.output_path)).run()
    assert result.player_form_diagnostic_status == "PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY"
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["player_xg_xa_gate_status"] == "DIAGNOSTIC_READY"
    assert row["big_chance_gate_status"] == "DIAGNOSTIC_READY"
    assert row["rolling_form_gate_status"] == "DIAGNOSTIC_READY"
    assert row["conversion_signal_gate_status"] == "DIAGNOSTIC_READY"
    assert row["main_creator_availability_gate_status"] == "DIAGNOSTIC_READY"
    assert row["main_scorer_availability_gate_status"] == "DIAGNOSTIC_READY"
    assert row["no_bet_player_form_safety_status"] == "BETTING_OUTPUT_DISABLED_BY_DESIGN"
    frame = pd.read_csv(input_result.output_path)
    frame.loc[0, "home_recent_xg_for"] = ""
    missing_path = tmp_path / "missing_rolling.csv"
    frame.to_csv(missing_path, index=False)
    missing = PlayerFormDiagnosticRunner(PlayerFormDiagnosticConfig(player_impact_rolling_form_input_path=missing_path)).run()
    missing_row = pd.read_csv(missing.output_path).iloc[0]
    assert missing_row["rolling_form_gate_status"] == "DIAGNOSTIC_GATE_REQUIRES_PLAYER_FORM_DATA"


def test_pipeline_bundle_excel_helper_and_audit_include_player_form_layer() -> None:
    command = run_match_analysis_preview(cross_provider_match_key="u-bundesliga-2024-001")
    assert command["command_status"] == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"
    assert command["market_movement_diagnostic_status"] == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    assert command["availability_diagnostic_status"] == "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
    assert command["player_impact_rolling_form_input_status"] == "PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY"
    assert command["player_form_diagnostic_status"] == "PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY"
    assert int(command["sheets_written"]) >= 14
    report = Path(str(command["human_report_path"])).read_text(encoding="utf-8")
    assert "Player/form diagnostic status" in report
    bundle = build_match_analysis_export_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001")
    bundle_dir = Path(str(bundle["export_bundle_dir"]))
    assert (bundle_dir / "player_impact_rolling_form_input_review.csv").exists()
    assert (bundle_dir / "player_form_diagnostic_review.csv").exists()
    helper = build_player_form_diagnostic_24_block_preview_helper()
    assert helper["recommendation"] == "PLAYER_FORM_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
    audit = audit_player_form_diagnostic_24_block_preview()
    assert audit["recommendation"] == "PLAYER_FORM_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
