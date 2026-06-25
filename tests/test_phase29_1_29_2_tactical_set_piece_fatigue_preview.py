# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.tactical_matchup_diagnostic_preview import TacticalMatchupDiagnosticConfig, TacticalMatchupDiagnosticRunner
from football_prediction_v19.analysis.tactical_set_piece_fatigue_input_preview import TacticalSetPieceFatigueInputConfig, TacticalSetPieceFatigueInputRunner
from scripts.audit_tactical_matchup_diagnostic_24_block_preview import audit_tactical_matchup_diagnostic_24_block_preview
from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview
from scripts.build_tactical_matchup_diagnostic_24_block_preview_helper import build_tactical_matchup_diagnostic_24_block_preview_helper
from scripts.run_match_analysis_preview import run_match_analysis_preview


def test_tactical_input_builds_deterministic_fixture() -> None:
    result = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(cross_provider_match_key="u-bundesliga-2024-001")).run()
    assert result.tactical_set_piece_fatigue_input_status == "TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY"
    assert result.rows_written == 1
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["cross_provider_match_key"] == "u-bundesliga-2024-001"
    assert str(row["network_calls_enabled"]).lower() == "false"
    assert "tactical_matchup_score" in row.index


def test_tactical_input_csv_unknown_ambiguous_and_missing_columns(tmp_path: Path) -> None:
    base = pd.read_csv(TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig()).run().output_path)
    path = tmp_path / "tactical.csv"
    pd.concat([base, base.assign(cross_provider_match_key="u-bundesliga-2024-002", home_team="Other")]).to_csv(path, index=False)
    ready = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(cross_provider_match_key="u-bundesliga-2024-001", tactical_input_path=path)).run()
    assert ready.tactical_set_piece_fatigue_input_status == "TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY"
    unknown = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(cross_provider_match_key="missing", tactical_input_path=path)).run()
    assert unknown.tactical_set_piece_fatigue_input_status == "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNKNOWN_MATCH"
    ambiguous = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(competition="Bundesliga", tactical_input_path=path)).run()
    assert ambiguous.tactical_set_piece_fatigue_input_status == "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_AMBIGUOUS_MATCH"
    bad = tmp_path / "bad.csv"
    base.drop(columns=["tactical_snapshot_source"]).to_csv(bad, index=False)
    missing = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(tactical_input_path=bad)).run()
    assert missing.tactical_set_piece_fatigue_input_status == "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"


def test_tactical_input_blocks_unsafe_and_surfaces_missing_optional(tmp_path: Path) -> None:
    unsafe = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(tactical_input_path="https://example.test/tactical.csv")).run()
    assert unsafe.tactical_set_piece_fatigue_input_status == "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNSAFE_PATH"
    frame = pd.read_csv(TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig()).run().output_path)
    frame.loc[0, "transition_matchup_note"] = ""
    path = tmp_path / "missing_optional.csv"
    frame.to_csv(path, index=False)
    result = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(tactical_input_path=path)).run()
    row = pd.read_csv(result.output_path).iloc[0]
    assert int(row["missing_tactical_fields_count"]) >= 1
    assert "transition_matchup_note" in str(row["missing_tactical_fields"])


def test_tactical_diagnostic_sets_gate_statuses_and_leaves_missing_values_missing(tmp_path: Path) -> None:
    input_result = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig()).run()
    result = TacticalMatchupDiagnosticRunner(TacticalMatchupDiagnosticConfig(tactical_set_piece_fatigue_input_path=input_result.output_path)).run()
    assert result.tactical_matchup_diagnostic_status == "TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY"
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["set_piece_xg_ratio_gate_status"] == "DIAGNOSTIC_READY"
    assert row["tactical_matchup_score_gate_status"] == "DIAGNOSTIC_READY"
    assert row["fatigue_modifier_gate_status"] == "DIAGNOSTIC_READY"
    assert row["xg_zone_correction_gate_status"] == "DIAGNOSTIC_READY"
    assert row["formation_matchup_gate_status"] == "DIAGNOSTIC_READY"
    assert row["transition_matchup_gate_status"] == "DIAGNOSTIC_READY"
    assert row["no_bet_tactical_safety_status"] == "BETTING_OUTPUT_DISABLED_BY_DESIGN"
    frame = pd.read_csv(input_result.output_path)
    frame["home_set_piece_xg_ratio"] = frame["home_set_piece_xg_ratio"].astype(object)
    frame.loc[0, "home_set_piece_xg_ratio"] = ""
    missing_path = tmp_path / "missing_set_piece.csv"
    frame.to_csv(missing_path, index=False)
    missing = TacticalMatchupDiagnosticRunner(TacticalMatchupDiagnosticConfig(tactical_set_piece_fatigue_input_path=missing_path)).run()
    missing_row = pd.read_csv(missing.output_path).iloc[0]
    assert missing_row["set_piece_xg_ratio_gate_status"] == "DIAGNOSTIC_GATE_REQUIRES_TACTICAL_DATA"


def test_pipeline_bundle_excel_helper_and_audit_include_tactical_layer() -> None:
    command = run_match_analysis_preview(cross_provider_match_key="u-bundesliga-2024-001")
    assert command["command_status"] == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"
    assert command["market_movement_diagnostic_status"] == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    assert command["availability_diagnostic_status"] == "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
    assert command["player_form_diagnostic_status"] == "PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY"
    assert command["tactical_set_piece_fatigue_input_status"] == "TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY"
    assert command["tactical_matchup_diagnostic_status"] == "TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY"
    assert int(command["sheets_written"]) >= 16
    report = Path(str(command["human_report_path"])).read_text(encoding="utf-8")
    assert "Tactical diagnostic status" in report
    bundle = build_match_analysis_export_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001")
    bundle_dir = Path(str(bundle["export_bundle_dir"]))
    assert (bundle_dir / "player_form_diagnostic_review.csv").exists()
    assert (bundle_dir / "tactical_set_piece_fatigue_input_review.csv").exists()
    assert (bundle_dir / "tactical_matchup_diagnostic_review.csv").exists()
    helper = build_tactical_matchup_diagnostic_24_block_preview_helper()
    assert helper["recommendation"] == "TACTICAL_MATCHUP_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
    audit = audit_tactical_matchup_diagnostic_24_block_preview()
    assert audit["recommendation"] == "TACTICAL_MATCHUP_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
