# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pandas as pd

from scripts.audit_real_match_analysis_command_preview import REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY as AUDIT_READY, run as run_audit
from scripts.build_real_match_analysis_command_preview_helper import run_workflow
from scripts.run_match_analysis_preview import run_match_analysis_preview
from football_prediction_v19.analysis.real_match_analysis_command_preview import (
    REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_AMBIGUOUS_MATCH,
    REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXCEL_EXPORT,
    REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNKNOWN_MATCH,
    REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNSAFE_PATH,
    REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY,
    RealMatchAnalysisCommandConfig,
    RealMatchAnalysisCommandRunner,
)

ROOT = Path(__file__).resolve().parents[1]
PROTECTED_FILES = [
    ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
    ROOT / "src" / "football_prediction_v19" / "recommended_market.py",
]
REQUIRED_ARTIFACT_TYPES = {
    "match_context_bundle", "context_human_input", "v19_diagnostic_synthesis",
    "v19_diagnostic_gate_matrix", "human_24_block_report", "export_bundle_manifest",
    "excel_workbook", "command_manifest", "command_summary",
}


def _hashes() -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in PROTECTED_FILES if path.exists()}


def _assert_hashes_unchanged(before: dict[Path, str]) -> None:
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def _openpyxl_available() -> bool:
    try:
        importlib.import_module("openpyxl")
        return True
    except ImportError:
        return False


def _assert_ready(summary: dict[str, object]) -> None:
    assert summary["command_status"] == REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY
    assert summary["match_context_bundle_status"] == "MATCH_CONTEXT_BUNDLE_PREVIEW_READY"
    assert summary["context_bridge_status"] == "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY"
    assert summary["v19_diagnostic_synthesis_status"] == "V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY"
    assert summary["v19_diagnostic_gate_matrix_status"] == "V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY"
    assert summary["human_24_block_report_status"] == "HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY"
    assert summary["export_bundle_status"] == "MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY"
    assert summary["excel_export_status"] == "MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY"
    assert summary["gates_evaluated"] >= 19
    assert summary["sections_rendered"] == 24
    assert summary["required_sections_rendered"] == 24
    assert summary["exported_files_count"] >= 6
    assert summary["sheets_written"] >= 8
    assert summary["workbook_file_exists"] is True
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert summary["staking_logic_enabled"] is False
    assert summary["roi_logic_enabled"] is False


def test_command_runner_builds_full_preview_by_cross_provider_key(tmp_path: Path) -> None:
    if not _openpyxl_available():
        return
    summary = run_match_analysis_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "real_match_analysis_command",
        base_dir=tmp_path,
    )
    _assert_ready(summary)
    assert Path(str(summary["human_report_path"])).exists()
    assert Path(str(summary["excel_workbook_path"])).exists()
    assert Path(str(summary["manifest_path"])).exists()
    assert Path(str(summary["summary_path"])).exists()


def test_command_runner_selection_modes(tmp_path: Path) -> None:
    if not _openpyxl_available():
        return
    common = {"output_dir": tmp_path / "outputs" / "analysis_preview" / "real_match_analysis_command", "base_dir": tmp_path}
    _assert_ready(run_match_analysis_preview(understat_provider_match_id="u-bundesliga-2024-001", **common))
    _assert_ready(run_match_analysis_preview(fbref_provider_match_id="fbref-bundesliga-2024-001", **common))
    _assert_ready(run_match_analysis_preview(home_team="Home FC", away_team="Away FC", match_date="2024-08-23", **common))
    _assert_ready(run_match_analysis_preview(competition="Bundesliga", season="2024", home_team="Home FC", away_team="Away FC", **common))


def test_command_blocks_unknown_ambiguous_unsafe_and_component_failure(tmp_path: Path) -> None:
    unknown = run_match_analysis_preview(
        cross_provider_match_key="missing",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "real_match_analysis_command",
        base_dir=tmp_path,
    )
    assert unknown["command_status"] == REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNKNOWN_MATCH

    ambiguous = run_match_analysis_preview(
        competition="Bundesliga",
        season="2024",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "real_match_analysis_command",
        base_dir=tmp_path,
    )
    assert ambiguous["command_status"] == REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_AMBIGUOUS_MATCH

    unsafe = RealMatchAnalysisCommandRunner(RealMatchAnalysisCommandConfig(
        output_dir=tmp_path / "data" / "processed",
        base_dir=tmp_path,
    )).run()
    assert unsafe.command_status == REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNSAFE_PATH

    component = RealMatchAnalysisCommandRunner(RealMatchAnalysisCommandConfig(
        excel_output_dir=tmp_path / "data" / "processed",
        base_dir=tmp_path,
    )).run()
    assert component.command_status in {REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNSAFE_PATH, REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXCEL_EXPORT}


def test_artifact_index_and_manifest_are_written(tmp_path: Path) -> None:
    if not _openpyxl_available():
        return
    summary = run_match_analysis_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "real_match_analysis_command",
        base_dir=tmp_path,
    )
    index = pd.read_csv(summary["artifact_index_path"])
    assert REQUIRED_ARTIFACT_TYPES.issubset(set(index["artifact_type"]))
    assert index["artifact_path"].astype(str).str.contains("outputs").all()
    assert index["preview_only"].astype(str).str.lower().eq("true").all()
    assert index["safe_for_review"].astype(str).str.lower().eq("true").all()
    manifest = pd.read_csv(summary["manifest_path"])
    for column in [
        "command_status", "match_context_bundle_status", "context_bridge_status",
        "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
        "human_24_block_report_status", "export_bundle_status", "excel_export_status",
    ]:
        assert column in manifest.columns
    summary_text = Path(str(summary["summary_path"])).read_text(encoding="utf-8").lower()
    index_text = Path(str(summary["artifact_index_path"])).with_suffix(".md").read_text(encoding="utf-8").lower()
    for forbidden in ["stake size", "return on investment", "super_a", "bet this", " units"]:
        assert forbidden not in summary_text
        assert forbidden not in index_text


def test_helper_and_audit_return_ready(tmp_path: Path) -> None:
    if not _openpyxl_available():
        return
    helper = run_workflow(tmp_path)
    _assert_ready(helper)
    assert helper["recommendation"] == REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY
    table, _markdown, rec = run_audit(
        command_manifest=helper["manifest_path"],
        output_dir=tmp_path / "outputs" / "diagnostics",
        base_dir=tmp_path,
    )
    assert rec == AUDIT_READY
    assert bool(table["preview_valid"].iloc[0])


def test_no_protected_logic_files_are_modified(tmp_path: Path) -> None:
    if not _openpyxl_available():
        return
    before = _hashes()
    summary = run_match_analysis_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "real_match_analysis_command",
        base_dir=tmp_path,
    )
    assert summary["command_status"] == REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY
    _assert_hashes_unchanged(before)
