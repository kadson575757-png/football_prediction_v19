# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.real_match_analysis_runner_preview import RealMatchAnalysisRunner, RealMatchAnalysisRunnerConfig
from scripts.audit_final_real_match_analysis_readiness_preview import audit_final_real_match_analysis_readiness_preview
from scripts.audit_real_match_artifact_acceptance_preview import audit_real_match_artifact_acceptance_preview
from scripts.build_filled_real_match_intake_pack_preview import build_filled_real_match_intake_pack_preview
from scripts.build_final_real_match_analysis_readiness_preview_helper import build_final_real_match_analysis_readiness_preview_helper
from scripts.build_real_match_analysis_runner_preview import build_real_match_analysis_runner_preview
from scripts.build_user_facing_real_match_report_preview import build_user_facing_real_match_report_preview
from scripts.run_match_analysis_preview import run_match_analysis_preview


def test_filled_intake_pack_creates_full_and_minimal_csvs() -> None:
    result = build_filled_real_match_intake_pack_preview()
    assert result["filled_real_match_intake_pack_status"] == "FILLED_REAL_MATCH_INTAKE_PACK_PREVIEW_READY"
    assert Path(str(result["filled_intake_path"])).exists()
    assert Path(str(result["minimal_intake_path"])).exists()
    assert int(result["columns_written"]) >= 90


def test_real_match_runner_full_and_minimal_surface_missing_optional() -> None:
    filled = build_filled_real_match_intake_pack_preview()
    full = build_real_match_analysis_runner_preview(real_match_intake_path=filled["filled_intake_path"])
    assert full["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    assert full["market_movement_diagnostic_status"] == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    assert full["tactical_matchup_diagnostic_status"] == "TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY"
    assert int(full["sheets_written"]) >= 16
    minimal = build_real_match_analysis_runner_preview(real_match_intake_path=filled["minimal_intake_path"])
    assert minimal["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    overlay = pd.read_csv("outputs/analysis_preview/manual_evidence_overlay/manual_evidence_overlay.csv").iloc[0]
    assert "MISSING_OPTIONAL" in str(overlay["availability_overlay_status"]) or "MISSING_OPTIONAL" in str(overlay["player_form_overlay_status"])


def test_real_match_runner_blocks_missing_required_and_unsafe(tmp_path: Path) -> None:
    filled = build_filled_real_match_intake_pack_preview()
    frame = pd.read_csv(filled["filled_intake_path"])
    bad_path = tmp_path / "bad.csv"
    frame.assign(home_team="").to_csv(bad_path, index=False)
    bad = RealMatchAnalysisRunner(RealMatchAnalysisRunnerConfig(real_match_intake_path=bad_path)).run()
    assert bad.real_match_analysis_runner_status == "REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_VALIDATION_FAILED"
    unsafe = RealMatchAnalysisRunner(RealMatchAnalysisRunnerConfig(real_match_intake_path="https://example.test/intake.csv")).run()
    assert unsafe.real_match_analysis_runner_status == "REAL_MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH"


def test_run_match_analysis_preview_intake_and_deterministic_compatibility() -> None:
    filled = build_filled_real_match_intake_pack_preview()
    intake = run_match_analysis_preview(real_match_intake=filled["filled_intake_path"])
    assert intake["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    deterministic = run_match_analysis_preview(cross_provider_match_key="u-bundesliga-2024-001")
    assert deterministic["command_status"] == "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"


def test_custom_manual_lazio_atalanta_intake_hands_off_to_all_layers() -> None:
    result = run_match_analysis_preview(real_match_intake="data/manual/real_match_intake.csv")
    assert result["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    assert result["real_match_input_pack_status"] == "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
    assert result["real_match_intake_validation_status"] == "REAL_MATCH_INTAKE_VALIDATION_READY"
    assert result["manual_evidence_overlay_status"] == "MANUAL_EVIDENCE_OVERLAY_PREVIEW_READY"
    assert result["odds_market_movement_input_status"] == "ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY"
    assert result["market_movement_diagnostic_status"] == "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
    assert result["lineups_availability_input_status"] == "LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY"
    assert result["availability_diagnostic_status"] == "AVAILABILITY_DIAGNOSTIC_PREVIEW_READY"
    assert result["player_impact_rolling_form_input_status"] == "PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY"
    assert result["player_form_diagnostic_status"] == "PLAYER_FORM_DIAGNOSTIC_PREVIEW_READY"
    assert result["tactical_set_piece_fatigue_input_status"] == "TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY"
    assert result["tactical_matchup_diagnostic_status"] == "TACTICAL_MATCHUP_DIAGNOSTIC_PREVIEW_READY"
    assert result["human_24_block_report_status"] == "HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY"
    assert result["export_bundle_status"] == "MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY"
    assert result["excel_export_status"] == "MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY"
    assert int(result["sections_rendered"]) == 24
    assert int(result["required_sections_rendered"]) == 24
    assert int(result["exported_files_count"]) == 14
    assert int(result["sheets_written"]) >= 16
    assert bool(result["workbook_file_exists"])
    assert result["home_team"] == "Lazio"
    assert result["away_team"] == "Atalanta"
    assert result["match_date"] == "2026-02-14"
    context = pd.read_csv("outputs/analysis_preview/context_bundle_human_input/context_bundle_human_input.csv", keep_default_na=False).iloc[0]
    assert context["home_team"] == "Lazio"
    assert context["away_team"] == "Atalanta"
    assert context["competition"] == "Serie A"
    assert context["match_date"] == "2026-02-14"
    assert context["cross_provider_match_key"] == "manual-serie-a-2025-26-lazio-atalanta-2026-02-14"
    assert context["understat_provider_match_id"] == ""
    assert context["fbref_provider_match_id"] == ""
    assert float(context["home_xg"]) == 48.18
    assert float(context["away_xg"]) == 70.82
    report = Path("outputs/analysis_preview/human_24_block_report/human_24_block_match_report_preview.md").read_text(encoding="utf-8")
    assert "Lazio vs Atalanta on 2026-02-14 (Serie A 2025/26)" in report
    assert "Home FC vs Away FC on 2024-08-23 (Bundesliga 2024)" not in report
    assert "Home FC" not in report
    assert "Away FC" not in report
    assert not any(bool(result[k]) for k in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"])


def test_user_report_acceptance_and_final_readiness() -> None:
    filled = build_filled_real_match_intake_pack_preview()
    runner = build_real_match_analysis_runner_preview(real_match_intake_path=filled["filled_intake_path"])
    assert runner["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    report = build_user_facing_real_match_report_preview()
    assert report["user_facing_real_match_report_status"] == "USER_FACING_REAL_MATCH_REPORT_PREVIEW_READY"
    assert int(report["sections_rendered"]) == 24
    assert bool(report["no_bet_section_rendered"])
    assert not bool(report["final_betting_tips_rendered"])
    assert not bool(report["stake_units_rendered"])
    assert not bool(report["roi_rendered"])
    assert not bool(report["super_a_promotion_rendered"])
    acceptance = audit_real_match_artifact_acceptance_preview()
    assert acceptance["real_match_artifact_acceptance_status"] == "REAL_MATCH_ARTIFACT_ACCEPTANCE_PREVIEW_READY"
    helper = build_final_real_match_analysis_readiness_preview_helper()
    assert helper["final_real_match_analysis_readiness_status"] == "FINAL_REAL_MATCH_ANALYSIS_READINESS_PREVIEW_READY"
    audit = audit_final_real_match_analysis_readiness_preview()
    assert audit["final_real_match_analysis_readiness_status"] == "FINAL_REAL_MATCH_ANALYSIS_READINESS_PREVIEW_READY"
    assert not bool(audit["network_calls_enabled"])
    assert not bool(audit["prediction_logic_enabled"])
    assert not bool(audit["betting_logic_enabled"])
    assert not bool(audit["staking_logic_enabled"])
    assert not bool(audit["roi_logic_enabled"])
