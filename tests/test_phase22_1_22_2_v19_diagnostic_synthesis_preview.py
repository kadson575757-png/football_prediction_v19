# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from scripts.audit_v19_diagnostic_24_block_report_preview import V19_DIAGNOSTIC_24_BLOCK_REPORT_PREVIEW_READY, run as run_audit
from scripts.build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview
from scripts.build_human_24_block_report_preview import build_human_24_block_report_preview
from scripts.build_v19_diagnostic_24_block_report_preview_helper import run_workflow
from scripts.build_v19_diagnostic_synthesis_preview import build_v19_diagnostic_synthesis_preview
from football_prediction_v19.analysis.human_24_block_report_preview import REQUIRED_SECTIONS
from football_prediction_v19.analysis.v19_diagnostic_synthesis_preview import (
    V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_AMBIGUOUS_MATCH,
    V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_INPUT,
    V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_COLUMNS,
    V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_VALUES,
    V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNKNOWN_MATCH,
    V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNSAFE_PATH,
    V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY,
    V19DiagnosticSynthesisConfig,
    V19DiagnosticSynthesisRunner,
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
    bridge = build_context_bundle_human_input_bridge_preview(
        cross_provider_match_key=key,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "context_bundle_human_input",
        base_dir=tmp_path,
    )
    return Path(str(bridge["human_input_output_path"]))


def test_v19_diagnostic_synthesis_builds_from_context_input(tmp_path: Path) -> None:
    human_input = _human_input(tmp_path)
    summary = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=human_input,
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert summary["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert summary["rows_diagnosed"] == 1
    assert summary["v19_model_synthesis_status"] == "DIAGNOSTIC_READY"
    assert summary["no_bet_safety_status"] == "BETTING_OUTPUT_DISABLED_BY_DESIGN"
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert summary["staking_logic_enabled"] is False
    assert summary["roi_logic_enabled"] is False
    output = pd.read_csv(summary["output_path"])
    assert "control_model_status" in output.columns
    assert "chaos_score_status" in output.columns
    assert "away_favorite_degradation_status" in output.columns


def test_v19_diagnostic_synthesis_builds_when_input_omitted(tmp_path: Path) -> None:
    summary = build_v19_diagnostic_synthesis_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
    )
    assert summary["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert Path(str(summary["output_path"])).exists()


def test_v19_diagnostic_selection_modes(tmp_path: Path) -> None:
    human_input = _human_input(tmp_path)
    common = {
        "context_human_input_path": human_input,
        "output_dir": tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        "base_dir": tmp_path,
        "build_missing": False,
    }
    assert build_v19_diagnostic_synthesis_preview(cross_provider_match_key="u-bundesliga-2024-001", **common)["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert build_v19_diagnostic_synthesis_preview(understat_provider_match_id="u-bundesliga-2024-001", **common)["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert build_v19_diagnostic_synthesis_preview(fbref_provider_match_id="fbref-bundesliga-2024-001", **common)["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert build_v19_diagnostic_synthesis_preview(home_team="Home FC", away_team="Away FC", match_date="2024-08-23", competition="Bundesliga", season="2024", **common)["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY


def test_v19_diagnostic_blocks_missing_unknown_ambiguous_and_unsafe(tmp_path: Path) -> None:
    missing = V19DiagnosticSynthesisRunner(V19DiagnosticSynthesisConfig(
        context_human_input_path=tmp_path / "missing.csv",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
    )).run()[0]
    assert missing.v19_diagnostic_synthesis_status == V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_INPUT

    human_input = _human_input(tmp_path)
    unknown = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=human_input,
        cross_provider_match_key="missing",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert unknown["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNKNOWN_MATCH

    frame = pd.read_csv(human_input)
    ambiguous_path = tmp_path / "ambiguous_human_input.csv"
    pd.concat([frame, frame], ignore_index=True).to_csv(ambiguous_path, index=False)
    ambiguous = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=ambiguous_path,
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert ambiguous["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_AMBIGUOUS_MATCH

    unsafe = V19DiagnosticSynthesisRunner(V19DiagnosticSynthesisConfig(
        context_human_input_path=human_input,
        output_dir=tmp_path / "data" / "processed",
        base_dir=tmp_path,
    )).run()[0]
    assert unsafe.v19_diagnostic_synthesis_status == V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_UNSAFE_PATH


def test_v19_diagnostic_blocks_missing_columns_and_values(tmp_path: Path) -> None:
    human_input = _human_input(tmp_path)
    broken_columns = tmp_path / "broken_columns.csv"
    pd.read_csv(human_input).drop(columns=["home_team"]).to_csv(broken_columns, index=False)
    missing_columns = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=broken_columns,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert missing_columns["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_COLUMNS

    broken_values = tmp_path / "broken_values.csv"
    frame = pd.read_csv(human_input)
    frame.loc[0, "home_team"] = ""
    frame.to_csv(broken_values, index=False)
    missing_values = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=broken_values,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert missing_values["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_BLOCKED_MISSING_REQUIRED_VALUES


def test_missing_optional_values_are_surfaced_not_filled(tmp_path: Path) -> None:
    human_input = _human_input(tmp_path, "u-bundesliga-2024-002")
    summary = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=human_input,
        cross_provider_match_key="u-bundesliga-2024-002",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert summary["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert summary["missing_optional_fields_count"] >= 1


def test_24_block_report_integrates_v19_diagnostic_sections(tmp_path: Path) -> None:
    human_input = _human_input(tmp_path)
    diagnostic = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=human_input,
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    report = build_human_24_block_report_preview(
        context_human_input_path=human_input,
        v19_diagnostic_synthesis_path=diagnostic["output_path"],
        output_dir=tmp_path / "outputs" / "analysis_preview" / "human_24_block_report",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert report["sections_rendered"] == 24
    assert report["required_sections_rendered"] == 24
    assert report["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    text = Path(str(report["report_output_path"])).read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert f"## {section}" in text
    assert "DIAGNOSTIC_READY" in text
    assert "Betting output is disabled in this diagnostic preview layer." in text
    assert "Production prediction logic is disabled by design." in text
    assert "stake size" not in text.lower()
    assert "roi" not in text.lower()
    assert "super_a" not in text.lower()


def test_helper_and_audit_return_ready(tmp_path: Path) -> None:
    helper = run_workflow(tmp_path)
    assert helper["recommendation"] == V19_DIAGNOSTIC_24_BLOCK_REPORT_PREVIEW_READY
    assert helper["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert helper["sections_rendered"] == 24
    assert helper["required_sections_rendered"] == 24
    assert helper["network_calls_enabled"] is False
    assert helper["prediction_logic_enabled"] is False
    assert helper["betting_logic_enabled"] is False
    assert helper["staking_logic_enabled"] is False
    assert helper["roi_logic_enabled"] is False

    table, _markdown, rec = run_audit(
        diagnostic_manifest=helper["diagnostic_manifest_path"],
        report_manifest=helper["report_manifest_path"],
        output_dir=tmp_path / "outputs" / "diagnostics",
        base_dir=tmp_path,
    )
    assert rec == V19_DIAGNOSTIC_24_BLOCK_REPORT_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])


def test_no_protected_logic_files_are_modified(tmp_path: Path) -> None:
    before = _hashes()
    helper = run_workflow(tmp_path)
    assert helper["recommendation"] == V19_DIAGNOSTIC_24_BLOCK_REPORT_PREVIEW_READY
    _assert_hashes_unchanged(before)
