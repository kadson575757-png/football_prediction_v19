# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.market_movement_diagnostic_preview import MarketMovementDiagnosticConfig, MarketMovementDiagnosticRunner
from football_prediction_v19.analysis.odds_market_movement_input_preview import OddsMarketMovementInputConfig, OddsMarketMovementInputRunner
from scripts.audit_market_movement_diagnostic_24_block_preview import audit_market_movement_diagnostic_24_block_preview
from scripts.build_market_movement_diagnostic_24_block_preview_helper import build_market_movement_diagnostic_24_block_preview_helper
from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview
from scripts.run_match_analysis_preview import run_match_analysis_preview


def test_odds_input_builds_deterministic_fixture() -> None:
    result = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig(cross_provider_match_key="u-bundesliga-2024-001")).run()
    assert result.odds_market_movement_input_status == "ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY"
    assert result.rows_written == 1
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["cross_provider_match_key"] == "u-bundesliga-2024-001"
    assert row["network_calls_enabled"] is False or str(row["network_calls_enabled"]).lower() == "false"


def test_odds_input_supports_csv_and_blocks_unknown_ambiguous_missing_columns(tmp_path: Path) -> None:
    base = pd.read_csv(OddsMarketMovementInputRunner(OddsMarketMovementInputConfig()).run().output_path)
    csv_path = tmp_path / "odds.csv"
    pd.concat([base, base.assign(cross_provider_match_key="u-bundesliga-2024-002", home_team="Other")]).to_csv(csv_path, index=False)
    ready = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig(cross_provider_match_key="u-bundesliga-2024-001", odds_input_path=csv_path)).run()
    assert ready.odds_market_movement_input_status == "ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY"
    unknown = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig(cross_provider_match_key="missing", odds_input_path=csv_path)).run()
    assert unknown.odds_market_movement_input_status == "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNKNOWN_MATCH"
    ambiguous = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig(competition="Bundesliga", odds_input_path=csv_path)).run()
    assert ambiguous.odds_market_movement_input_status == "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_AMBIGUOUS_MATCH"
    bad = tmp_path / "bad.csv"
    base.drop(columns=["home_open_odds"]).to_csv(bad, index=False)
    missing = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig(odds_input_path=bad)).run()
    assert missing.odds_market_movement_input_status == "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"


def test_odds_input_blocks_unsafe_and_surfaces_missing_optional(tmp_path: Path) -> None:
    unsafe = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig(odds_input_path="https://example.test/odds.csv")).run()
    assert unsafe.odds_market_movement_input_status == "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNSAFE_PATH"
    frame = pd.read_csv(OddsMarketMovementInputRunner(OddsMarketMovementInputConfig()).run().output_path)
    frame.loc[0, "dnb_home_odds"] = ""
    frame.loc[0, "dnb_away_odds"] = ""
    path = tmp_path / "missing_optional.csv"
    frame.to_csv(path, index=False)
    result = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig(odds_input_path=path)).run()
    row = pd.read_csv(result.output_path).iloc[0]
    assert result.odds_market_movement_input_status == "ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY"
    assert int(row["missing_market_fields_count"]) >= 2


def test_market_movement_diagnostic_computes_explicit_movements_only() -> None:
    odds = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig()).run()
    result = MarketMovementDiagnosticRunner(MarketMovementDiagnosticConfig(odds_market_movement_input_path=odds.output_path)).run()
    assert result.market_movement_diagnostic_status == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    row = pd.read_csv(result.output_path).iloc[0]
    assert row["home_odds_movement_direction"] == "SHORTENED"
    assert float(row["home_odds_movement_pct"]) < 0
    assert row["odds_availability_gate_status"] == "DIAGNOSTIC_READY"
    assert row["no_bet_market_safety_status"] == "BETTING_OUTPUT_DISABLED_BY_DESIGN"


def test_market_movement_diagnostic_leaves_missing_values_missing(tmp_path: Path) -> None:
    odds = OddsMarketMovementInputRunner(OddsMarketMovementInputConfig()).run()
    frame = pd.read_csv(odds.output_path)
    frame.loc[0, "away_current_odds"] = ""
    path = tmp_path / "missing_current.csv"
    frame.to_csv(path, index=False)
    result = MarketMovementDiagnosticRunner(MarketMovementDiagnosticConfig(odds_market_movement_input_path=path)).run()
    row = pd.read_csv(result.output_path).iloc[0]
    assert pd.isna(row["away_odds_movement_direction"]) or str(row["away_odds_movement_direction"]).strip() == ""
    assert row["odds_availability_gate_status"] == "DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA"


def test_one_command_bundle_excel_helper_and_audit_include_market_layer() -> None:
    command = run_match_analysis_preview(cross_provider_match_key="u-bundesliga-2024-001")
    assert command["command_status"] == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"
    assert command["odds_market_movement_input_status"] == "ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY"
    assert command["market_movement_diagnostic_status"] == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    assert int(command["sheets_written"]) >= 10
    report = Path(str(command["human_report_path"])).read_text(encoding="utf-8")
    assert "Market movement diagnostic status" in report
    bundle = build_match_analysis_export_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001")
    bundle_dir = Path(str(bundle["export_bundle_dir"]))
    assert (bundle_dir / "odds_market_movement_input_review.csv").exists()
    assert (bundle_dir / "market_movement_diagnostic_review.csv").exists()
    helper = build_market_movement_diagnostic_24_block_preview_helper()
    assert helper["recommendation"] == "MARKET_MOVEMENT_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
    audit = audit_market_movement_diagnostic_24_block_preview()
    assert audit["recommendation"] == "MARKET_MOVEMENT_DIAGNOSTIC_24_BLOCK_PREVIEW_READY"
