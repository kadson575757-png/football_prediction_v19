# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from scripts.audit_match_analysis_runner_24_block_preview import MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW_READY, run as run_audit
from scripts.build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview
from scripts.build_human_24_block_report_preview import build_human_24_block_report_preview
from scripts.build_match_analysis_runner_24_block_preview_helper import run_workflow as run_helper
from scripts.build_match_analysis_runner_preview import build_match_analysis_runner_preview
from football_prediction_v19.analysis.human_24_block_report_preview import (
    HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT,
    HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS,
    HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH,
    HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY,
    REQUIRED_SECTIONS,
    Human24BlockReportConfig,
    Human24BlockReportRenderer,
)
from football_prediction_v19.analysis.match_analysis_runner_preview import (
    MATCH_ANALYSIS_RUNNER_BLOCKED_AMBIGUOUS_MATCH,
    MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BRIDGE,
    MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BUNDLE,
    MATCH_ANALYSIS_RUNNER_BLOCKED_MISSING_REQUIRED_VALUES,
    MATCH_ANALYSIS_RUNNER_BLOCKED_REPORT,
    MATCH_ANALYSIS_RUNNER_BLOCKED_UNKNOWN_MATCH,
    MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH,
    MATCH_ANALYSIS_RUNNER_PREVIEW_READY,
    MatchAnalysisRunnerConfig,
    MatchAnalysisRunnerPreviewRunner,
)

ROOT = Path(__file__).resolve().parents[1]
PROTECTED_FILES = [
    ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
    ROOT / "src" / "football_prediction_v19" / "recommended_market.py",
]


def _hashes() -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in PROTECTED_FILES if path.exists()}


def _assert_hashes_unchanged(before: dict[Path, str]) -> None:
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def _human_input(tmp_path: Path, key: str = "u-bundesliga-2024-001") -> Path:
    bridge = build_context_bundle_human_input_bridge_preview(cross_provider_match_key=key, output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path)
    return Path(str(bridge["human_input_output_path"]))


def test_builds_24_block_report_from_context_human_input(tmp_path: Path) -> None:
    human_input = _human_input(tmp_path)
    summary = build_human_24_block_report_preview(context_human_input_path=human_input, output_dir=tmp_path / "outputs" / "analysis_preview" / "human_24_block_report", base_dir=tmp_path, build_missing=False)
    assert summary["human_24_block_report_status"] == HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY
    assert summary["sections_rendered"] == 24
    assert summary["required_sections_rendered"] == 24
    text = Path(str(summary["report_output_path"])).read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert f"## {section}" in text
    assert "Understat xG/xGA Snapshot" in text
    assert "FBref Team / Match Stats Snapshot" in text
    assert "Contradictions / Data Gaps" in text
    assert "No-Bet / Safety List" in text
    assert "not executed in this preview layer" in text


def test_builds_report_when_input_is_omitted(tmp_path: Path) -> None:
    summary = build_human_24_block_report_preview(output_dir=tmp_path / "outputs" / "analysis_preview" / "human_24_block_report", base_dir=tmp_path)
    assert summary["human_24_block_report_status"] == HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY
    assert summary["sections_rendered"] == 24


def test_runner_selection_modes(tmp_path: Path) -> None:
    common = {"output_dir": tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner", "base_dir": tmp_path}
    assert build_match_analysis_runner_preview(cross_provider_match_key="u-bundesliga-2024-001", **common)["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_PREVIEW_READY
    assert build_match_analysis_runner_preview(understat_provider_match_id="u-bundesliga-2024-001", **common)["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_PREVIEW_READY
    assert build_match_analysis_runner_preview(fbref_provider_match_id="fbref-bundesliga-2024-001", **common)["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_PREVIEW_READY
    assert build_match_analysis_runner_preview(home_team="Home FC", away_team="Away FC", match_date="2024-08-23", competition="Bundesliga", season="2024", **common)["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_PREVIEW_READY


def test_runner_blocks_unknown_ambiguous_and_unsafe(tmp_path: Path) -> None:
    common = {"output_dir": tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner", "base_dir": tmp_path}
    assert build_match_analysis_runner_preview(cross_provider_match_key="missing", **common)["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_BLOCKED_UNKNOWN_MATCH
    assert build_match_analysis_runner_preview(**common)["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_BLOCKED_AMBIGUOUS_MATCH
    unsafe = MatchAnalysisRunnerPreviewRunner(MatchAnalysisRunnerConfig(cross_provider_match_key="u-bundesliga-2024-001", output_dir=tmp_path / "data" / "processed", base_dir=tmp_path)).run()
    assert unsafe.match_analysis_runner_status == MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH
    unsafe_input = MatchAnalysisRunnerPreviewRunner(MatchAnalysisRunnerConfig(cross_provider_match_key="u-bundesliga-2024-001", understat_normalized_input=tmp_path / "data" / "processed" / "u.csv", base_dir=tmp_path)).run()
    assert unsafe_input.match_analysis_runner_status == MATCH_ANALYSIS_RUNNER_BLOCKED_UNSAFE_PATH


def test_runner_blocks_context_bundle_bridge_and_report_failures(tmp_path: Path) -> None:
    context_fail = build_match_analysis_runner_preview(match_context_bundle_path=tmp_path / "missing_bundle.csv", output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner", base_dir=tmp_path)
    assert context_fail["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_BLOCKED_CONTEXT_BRIDGE

    bad_context = tmp_path / "bad_context.csv"
    bad_context.write_text("context_bundle_id\nx\n", encoding="utf-8")
    bridge_fail = build_match_analysis_runner_preview(match_context_bundle_path=bad_context, output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner", base_dir=tmp_path)
    assert bridge_fail["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_BLOCKED_MISSING_REQUIRED_VALUES

    bad_human = tmp_path / "bad_human.csv"
    bad_human.write_text("analysis_input_id\nx\n", encoding="utf-8")
    report_fail = build_match_analysis_runner_preview(context_human_input_path=bad_human, cross_provider_match_key="u-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner", base_dir=tmp_path)
    assert report_fail["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_BLOCKED_REPORT


def test_missing_optional_values_are_surfaced_not_inferred(tmp_path: Path) -> None:
    summary = build_match_analysis_runner_preview(cross_provider_match_key="u-bundesliga-2024-002", output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner", base_dir=tmp_path)
    assert summary["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_PREVIEW_READY
    assert summary["missing_optional_fields_count"] >= 1
    text = Path(str(summary["report_output_path"])).read_text(encoding="utf-8")
    assert "preview gaps are surfaced" in text.lower()
    assert "not provided" in text.lower() or "not available in this preview layer" in text.lower()


def test_report_blocks_missing_input_missing_columns_and_unsafe_paths(tmp_path: Path) -> None:
    missing = Human24BlockReportRenderer(Human24BlockReportConfig(context_human_input_path=tmp_path / "missing.csv", output_dir=tmp_path / "outputs" / "analysis_preview" / "human_24_block_report", base_dir=tmp_path)).run()[0]
    assert missing.human_24_block_report_status == HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT
    human_input = _human_input(tmp_path)
    broken = tmp_path / "broken_human.csv"
    pd.read_csv(human_input).drop(columns=["home_team"]).to_csv(broken, index=False)
    missing_columns = Human24BlockReportRenderer(Human24BlockReportConfig(context_human_input_path=broken, output_dir=tmp_path / "outputs" / "analysis_preview" / "human_24_block_report", base_dir=tmp_path)).run()[0]
    assert missing_columns.human_24_block_report_status == HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS
    unsafe = Human24BlockReportRenderer(Human24BlockReportConfig(context_human_input_path=human_input, output_dir=tmp_path / "data" / "processed", base_dir=tmp_path)).run()[0]
    assert unsafe.human_24_block_report_status == HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH


def test_helper_and_audit_return_ready(tmp_path: Path) -> None:
    helper = run_helper(tmp_path)
    assert helper["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_PREVIEW_READY
    assert helper["match_context_bundle_status"] == "MATCH_CONTEXT_BUNDLE_PREVIEW_READY"
    assert helper["context_bridge_status"] == "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY"
    assert helper["human_24_block_report_status"] == HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY
    assert helper["sections_rendered"] == 24
    assert helper["required_sections_rendered"] == 24
    assert helper["network_calls_enabled"] is False
    assert helper["prediction_logic_enabled"] is False
    assert helper["betting_logic_enabled"] is False

    table, _markdown, rec = run_audit(runner_manifest=helper["manifest_path"], output_dir=tmp_path / "outputs" / "diagnostics", base_dir=tmp_path)
    assert rec == MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])


def test_no_protected_logic_files_are_modified(tmp_path: Path) -> None:
    before = _hashes()
    summary = build_match_analysis_runner_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner", base_dir=tmp_path)
    assert summary["match_analysis_runner_status"] == MATCH_ANALYSIS_RUNNER_PREVIEW_READY
    _assert_hashes_unchanged(before)
