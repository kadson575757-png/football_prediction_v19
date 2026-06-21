# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from scripts.audit_context_bundle_to_human_report_preview import CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW_READY, run as run_flow_audit
from scripts.build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview
from scripts.build_context_bundle_to_human_report_preview_helper import run_workflow as run_combined_helper
from scripts.build_context_enriched_human_report_preview import build_context_enriched_human_report_preview
from scripts.build_match_context_bundle_preview import build_match_context_bundle_preview
from football_prediction_v19.analysis.context_bundle_human_input_bridge_preview import (
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_AMBIGUOUS_MATCH,
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_CONTEXT_INPUT,
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_COLUMNS,
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_VALUES,
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNKNOWN_MATCH,
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNSAFE_PATH,
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_OPTIONAL_VALUES_MISSING,
    CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY,
    HUMAN_INPUT_COLUMNS,
    MANIFEST_COLUMNS as BRIDGE_MANIFEST_COLUMNS,
    ContextBundleHumanInputBridgeConfig,
    ContextBundleHumanInputBridgeRunner,
)
from football_prediction_v19.analysis.context_enriched_human_report_preview import (
    CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_INPUT,
    CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS,
    CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_UNSAFE_PATH,
    CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY,
    MANIFEST_COLUMNS as REPORT_MANIFEST_COLUMNS,
    ContextEnrichedHumanReportConfig,
    ContextEnrichedHumanReportRunner,
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


def _bundle(tmp_path: Path, key: str = "u-bundesliga-2024-001") -> Path:
    summary = build_match_context_bundle_preview(cross_provider_match_key=key, output_dir=tmp_path / "outputs" / "analysis_preview" / "match_context_bundle", base_dir=tmp_path)
    return Path(str(summary["output_path"]))


def _bridge(tmp_path: Path, key: str = "u-bundesliga-2024-001") -> dict[str, object]:
    bundle = _bundle(tmp_path, key)
    return build_context_bundle_human_input_bridge_preview(match_context_bundle_path=bundle, cross_provider_match_key=key, output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path, build_missing=False)


def test_builds_context_bundle_human_input_bridge_from_context_bundle(tmp_path: Path) -> None:
    summary = _bridge(tmp_path)
    assert summary["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
    assert summary["rows_written"] == 1
    assert summary["candidates_matched"] == 1
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    human = pd.read_csv(summary["human_input_output_path"])
    assert set(HUMAN_INPUT_COLUMNS).issubset(human.columns)
    assert human["home_xg"].astype(str).iloc[0] == "1.82"
    assert human["home_possession"].astype(str).iloc[0] == "56"


def test_builds_bridge_when_input_is_omitted(tmp_path: Path) -> None:
    summary = build_context_bundle_human_input_bridge_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path)
    assert summary["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
    assert summary["rows_written"] == 1


def test_bridge_selection_modes(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    kwargs = {"match_context_bundle_path": bundle, "output_dir": tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", "base_dir": tmp_path, "build_missing": False}
    assert build_context_bundle_human_input_bridge_preview(cross_provider_match_key="u-bundesliga-2024-001", **kwargs)["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
    assert build_context_bundle_human_input_bridge_preview(understat_provider_match_id="u-bundesliga-2024-001", **kwargs)["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
    assert build_context_bundle_human_input_bridge_preview(fbref_provider_match_id="fbref-bundesliga-2024-001", **kwargs)["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
    assert build_context_bundle_human_input_bridge_preview(home_team="Home FC", away_team="Away FC", match_date="2024-08-23", competition="Bundesliga", season="2024", **kwargs)["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY


def test_bridge_blocks_missing_unknown_ambiguous_missing_columns_values_and_unsafe(tmp_path: Path) -> None:
    missing = build_context_bundle_human_input_bridge_preview(match_context_bundle_path=tmp_path / "missing.csv", output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path, build_missing=False)
    assert missing["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_CONTEXT_INPUT

    bundle = _bundle(tmp_path)
    unknown = build_context_bundle_human_input_bridge_preview(match_context_bundle_path=bundle, cross_provider_match_key="missing", output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path, build_missing=False)
    assert unknown["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNKNOWN_MATCH

    two = tmp_path / "two_bundle.csv"
    frame = pd.concat([pd.read_csv(bundle), pd.read_csv(bundle)], ignore_index=True)
    frame.to_csv(two, index=False)
    ambiguous = build_context_bundle_human_input_bridge_preview(match_context_bundle_path=two, output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path, build_missing=False)
    assert ambiguous["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_AMBIGUOUS_MATCH

    broken = tmp_path / "broken_bundle.csv"
    pd.read_csv(bundle).drop(columns=["home_team"]).to_csv(broken, index=False)
    missing_columns = build_context_bundle_human_input_bridge_preview(match_context_bundle_path=broken, output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path, build_missing=False)
    assert missing_columns["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_COLUMNS

    missing_values_path = tmp_path / "missing_values_bundle.csv"
    values = pd.read_csv(bundle)
    values.loc[0, "home_team"] = ""
    values.to_csv(missing_values_path, index=False)
    missing_values = build_context_bundle_human_input_bridge_preview(match_context_bundle_path=missing_values_path, output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path, build_missing=False)
    assert missing_values["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_VALUES

    unsafe = ContextBundleHumanInputBridgeRunner(ContextBundleHumanInputBridgeConfig(match_context_bundle_path=bundle, output_dir=tmp_path / "data" / "processed", base_dir=tmp_path)).run()[0]
    assert unsafe.context_bridge_status == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNSAFE_PATH
    unsafe_input = ContextBundleHumanInputBridgeRunner(ContextBundleHumanInputBridgeConfig(match_context_bundle_path=tmp_path / "data" / "processed" / "bundle.csv", output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=tmp_path)).run()[0]
    assert unsafe_input.context_bridge_status == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNSAFE_PATH


def test_bridge_surfaces_missing_optional_and_writes_outputs(tmp_path: Path) -> None:
    summary = _bridge(tmp_path, key="u-bundesliga-2024-002")
    assert summary["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
    assert summary["missing_optional_fields_count"] >= 1
    human = pd.read_csv(summary["human_input_output_path"])
    manifest = pd.read_csv(summary["manifest_path"])
    assert set(BRIDGE_MANIFEST_COLUMNS).issubset(manifest.columns)
    assert Path(str(summary["summary_path"])).exists()
    assert human["normalization_warning"].astype(str).str.contains(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_OPTIONAL_VALUES_MISSING).any()
    assert human["away_clearances"].fillna("").iloc[0] == ""


def test_builds_context_enriched_human_report_and_contains_required_sections(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    report = build_context_enriched_human_report_preview(context_human_input_path=bridge["human_input_output_path"], output_dir=tmp_path / "outputs" / "analysis_preview" / "context_enriched_human_report", base_dir=tmp_path, build_missing=False)
    assert report["context_report_status"] == CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY
    assert report["rows_reported"] == 1
    assert report["sections_rendered"] >= 8
    text = Path(str(report["report_output_path"])).read_text(encoding="utf-8")
    for expected in ["Understat xG/xGA snapshot", "FBref team/match stats snapshot", "Data quality", "Preview-only model safety note", "No betting/staking note"]:
        assert expected in text
    assert "betting tips" in text.lower()
    manifest = pd.read_csv(report["manifest_path"])
    assert set(REPORT_MANIFEST_COLUMNS).issubset(manifest.columns)


def test_report_blocks_missing_input_missing_columns_and_unsafe_paths(tmp_path: Path) -> None:
    missing = ContextEnrichedHumanReportRunner(ContextEnrichedHumanReportConfig(context_human_input_path=tmp_path / "missing.csv", output_dir=tmp_path / "outputs" / "analysis_preview" / "context_enriched_human_report", base_dir=tmp_path)).run()[0]
    assert missing.context_report_status == CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_INPUT

    bridge = _bridge(tmp_path)
    broken = tmp_path / "broken_human.csv"
    pd.read_csv(bridge["human_input_output_path"]).drop(columns=["home_team"]).to_csv(broken, index=False)
    missing_columns = ContextEnrichedHumanReportRunner(ContextEnrichedHumanReportConfig(context_human_input_path=broken, output_dir=tmp_path / "outputs" / "analysis_preview" / "context_enriched_human_report", base_dir=tmp_path)).run()[0]
    assert missing_columns.context_report_status == CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS

    unsafe = ContextEnrichedHumanReportRunner(ContextEnrichedHumanReportConfig(context_human_input_path=bridge["human_input_output_path"], output_dir=tmp_path / "data" / "processed", base_dir=tmp_path)).run()[0]
    assert unsafe.context_report_status == CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_UNSAFE_PATH


def test_helper_and_audit_return_ready(tmp_path: Path) -> None:
    helper = run_combined_helper(tmp_path)
    assert helper["context_bundle_status"] == "MATCH_CONTEXT_BUNDLE_PREVIEW_READY"
    assert helper["context_bridge_status"] == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
    assert helper["context_report_status"] == CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY
    assert helper["rows_joined"] == 1
    assert helper["rows_written"] == 1
    assert helper["rows_reported"] == 1
    assert helper["sections_rendered"] >= 8
    assert helper["network_calls_enabled"] is False
    assert helper["prediction_logic_enabled"] is False
    assert helper["betting_logic_enabled"] is False

    table, _markdown, rec = run_flow_audit(output_dir=tmp_path / "outputs" / "diagnostics", base_dir=tmp_path)
    assert rec == CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])


def test_no_protected_logic_files_are_modified(tmp_path: Path) -> None:
    before = _hashes()
    helper = run_combined_helper(tmp_path)
    assert helper["context_report_status"] == CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY
    _assert_hashes_unchanged(before)
