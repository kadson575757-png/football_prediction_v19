# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pandas as pd

from scripts.audit_match_analysis_export_excel_preview import MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW_READY, run as run_audit
from scripts.build_match_analysis_excel_export_preview import build_match_analysis_excel_export_preview
from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview
from scripts.build_match_analysis_export_excel_preview_helper import run_workflow
from football_prediction_v19.analysis.match_analysis_excel_export_preview import (
    EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL,
    EXCEL_EXPORT_BLOCKED_UNSAFE_PATH,
    MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY,
    MatchAnalysisExcelExportConfig,
    MatchAnalysisExcelExportRunner,
)
from football_prediction_v19.analysis.match_analysis_export_bundle_preview import (
    MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH,
    MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNKNOWN_MATCH,
    MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNSAFE_PATH,
    MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY,
    MatchAnalysisExportBundleConfig,
    MatchAnalysisExportBundleRunner,
)

ROOT = Path(__file__).resolve().parents[1]
PROTECTED_FILES = [
    ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
    ROOT / "src" / "football_prediction_v19" / "recommended_market.py",
]
REQUIRED_EXPORT_FILES = [
    "match_analysis_export_bundle_manifest.csv",
    "match_analysis_export_bundle_summary.md",
    "match_identity.csv",
    "context_human_input_review.csv",
    "v19_diagnostic_synthesis_review.csv",
    "v19_diagnostic_gate_matrix_review.csv",
    "report_sections_review.csv",
    "export_safety_flags.csv",
]
REQUIRED_SHEETS = [
    "README", "Match Identity", "Context Human Input", "v19 Diagnostic Synthesis",
    "v19 Gate Matrix", "24 Block Report Sections", "Safety Flags", "Export Manifest",
]


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


def test_builds_match_analysis_export_bundle(tmp_path: Path) -> None:
    summary = build_match_analysis_export_bundle_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_export_bundle",
        base_dir=tmp_path,
    )
    assert summary["export_bundle_status"] == MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY
    assert summary["exported_files_count"] >= 6
    assert summary["sections_rendered"] == 24
    assert summary["required_sections_rendered"] == 24
    assert summary["gates_evaluated"] >= 19
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert summary["staking_logic_enabled"] is False
    assert summary["roi_logic_enabled"] is False
    bundle_dir = Path(str(summary["export_bundle_dir"]))
    for filename in REQUIRED_EXPORT_FILES:
        assert (bundle_dir / filename).exists()


def test_export_bundle_blocks_unknown_ambiguous_and_unsafe(tmp_path: Path) -> None:
    unknown = build_match_analysis_export_bundle_preview(
        cross_provider_match_key="missing",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_export_bundle",
        base_dir=tmp_path,
    )
    assert unknown["export_bundle_status"] == MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNKNOWN_MATCH

    ambiguous_context = tmp_path / "ambiguous_context.csv"
    frame = pd.DataFrame([
        {"analysis_input_id": "a", "match_date": "2024-01-01", "competition": "Bundesliga", "season": "2024", "home_team": "A", "away_team": "B", "understat_provider_match_id": "u1", "fbref_provider_match_id": "f1", "cross_provider_match_key": "k"},
        {"analysis_input_id": "b", "match_date": "2024-01-02", "competition": "Bundesliga", "season": "2024", "home_team": "C", "away_team": "D", "understat_provider_match_id": "u2", "fbref_provider_match_id": "f2", "cross_provider_match_key": "k2"},
    ])
    frame.to_csv(ambiguous_context, index=False)
    dummy = tmp_path / "dummy.csv"
    pd.DataFrame([{"x": 1}]).to_csv(dummy, index=False)
    report = tmp_path / "report.md"
    report.write_text("## One\nbody\n", encoding="utf-8")
    ambiguous = MatchAnalysisExportBundleRunner(MatchAnalysisExportBundleConfig(
        match_analysis_runner_manifest_path=dummy,
        context_human_input_path=ambiguous_context,
        v19_diagnostic_synthesis_path=dummy,
        v19_diagnostic_gate_matrix_path=dummy,
        human_24_block_report_path=report,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_export_bundle",
        base_dir=tmp_path,
    )).run()
    assert ambiguous.export_bundle_status == MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH

    unsafe = MatchAnalysisExportBundleRunner(MatchAnalysisExportBundleConfig(
        output_dir=tmp_path / "data" / "processed",
        base_dir=tmp_path,
    )).run()
    assert unsafe.export_bundle_status == MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNSAFE_PATH


def test_excel_export_builds_workbook_from_bundle(tmp_path: Path) -> None:
    if not _openpyxl_available():
        return
    bundle = build_match_analysis_export_bundle_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_export_bundle",
        base_dir=tmp_path,
    )
    excel = build_match_analysis_excel_export_preview(
        export_bundle_dir=bundle["export_bundle_dir"],
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_excel_export",
        base_dir=tmp_path,
    )
    assert excel["excel_export_status"] == MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY
    assert excel["workbook_file_exists"] is True
    assert excel["sheets_written"] >= 8
    openpyxl = importlib.import_module("openpyxl")
    wb = openpyxl.load_workbook(excel["workbook_output_path"], read_only=True, data_only=True)
    try:
        assert all(sheet in wb.sheetnames for sheet in REQUIRED_SHEETS)
        readme = " ".join(str(cell or "") for row in wb["README"].iter_rows(values_only=True) for cell in row).lower()
        flags = " ".join(str(cell or "") for row in wb["Safety Flags"].iter_rows(values_only=True) for cell in row).lower()
        assert "preview" in readme
        assert "production prediction logic is not executed" in readme
        assert "network_calls_enabled" in flags
        assert "false" in flags
        for forbidden in ["stake size", "return on investment", "super_a", "bet this", " units"]:
            assert forbidden not in readme
            assert forbidden not in flags
    finally:
        wb.close()


def test_excel_export_builds_bundle_when_missing_and_blocks_unsafe(tmp_path: Path) -> None:
    if _openpyxl_available():
        excel = build_match_analysis_excel_export_preview(
            output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_excel_export",
            base_dir=tmp_path,
        )
        assert excel["excel_export_status"] == MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY
        assert excel["workbook_file_exists"] is True
    unsafe = MatchAnalysisExcelExportRunner(MatchAnalysisExcelExportConfig(
        output_dir=tmp_path / "data" / "processed",
        base_dir=tmp_path,
    )).run()
    assert unsafe.excel_export_status == EXCEL_EXPORT_BLOCKED_UNSAFE_PATH


def test_excel_export_handles_missing_openpyxl(monkeypatch, tmp_path: Path) -> None:
    original = importlib.import_module

    def fake_import(name: str, package: str | None = None):
        if name == "openpyxl":
            raise ImportError("missing")
        return original(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    result = MatchAnalysisExcelExportRunner(MatchAnalysisExcelExportConfig(
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_excel_export",
        base_dir=tmp_path,
    )).run()
    assert result.excel_export_status == EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL


def test_helper_and_audit_return_ready_when_openpyxl_available(tmp_path: Path) -> None:
    if not _openpyxl_available():
        return
    helper = run_workflow(tmp_path)
    assert helper["export_bundle_status"] == MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY
    assert helper["excel_export_status"] == MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY
    assert helper["exported_files_count"] >= 6
    assert helper["sheets_written"] >= 8
    assert helper["workbook_file_exists"] is True
    assert helper["gates_evaluated"] >= 19
    assert helper["sections_rendered"] == 24
    assert helper["required_sections_rendered"] == 24
    table, _markdown, rec = run_audit(
        export_bundle_manifest=tmp_path / "outputs" / "analysis_preview" / "match_analysis_export_bundle" / "match_analysis_export_bundle_manifest.csv",
        excel_manifest=tmp_path / "outputs" / "analysis_preview" / "match_analysis_excel_export" / "match_analysis_excel_export_manifest.csv",
        output_dir=tmp_path / "outputs" / "diagnostics",
        base_dir=tmp_path,
    )
    assert rec == MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])


def test_no_protected_logic_files_are_modified(tmp_path: Path) -> None:
    before = _hashes()
    summary = build_match_analysis_export_bundle_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_export_bundle",
        base_dir=tmp_path,
    )
    assert summary["export_bundle_status"] == MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY
    _assert_hashes_unchanged(before)
