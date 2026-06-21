# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from scripts.audit_v19_diagnostic_gate_matrix_24_block_preview import V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW_READY, run as run_audit
from scripts.build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview
from scripts.build_human_24_block_report_preview import build_human_24_block_report_preview
from scripts.build_match_analysis_runner_preview import build_match_analysis_runner_preview
from scripts.build_v19_diagnostic_gate_matrix_24_block_preview_helper import run_workflow
from scripts.build_v19_diagnostic_gate_matrix_preview import build_v19_diagnostic_gate_matrix_preview
from scripts.build_v19_diagnostic_synthesis_preview import build_v19_diagnostic_synthesis_preview
from football_prediction_v19.analysis.human_24_block_report_preview import REQUIRED_SECTIONS
from football_prediction_v19.analysis.v19_diagnostic_gate_matrix_preview import (
    DIAGNOSTIC_GATE_DISABLED_NO_BETTING,
    DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE,
    V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_AMBIGUOUS_MATCH,
    V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_INPUT,
    V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_COLUMNS,
    V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_VALUES,
    V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNKNOWN_MATCH,
    V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNSAFE_PATH,
    V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY,
    V19DiagnosticGateMatrixConfig,
    V19DiagnosticGateMatrixRunner,
)
from football_prediction_v19.analysis.v19_diagnostic_synthesis_preview import V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY

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


def _synthesis(tmp_path: Path, key: str = "u-bundesliga-2024-001") -> dict[str, object]:
    human_input = _human_input(tmp_path, key)
    return build_v19_diagnostic_synthesis_preview(
        context_human_input_path=human_input,
        cross_provider_match_key=key,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )


def test_gate_matrix_builds_from_deterministic_synthesis(tmp_path: Path) -> None:
    synthesis = _synthesis(tmp_path)
    summary = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=synthesis["output_path"],
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert summary["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert summary["gates_evaluated"] >= 19
    assert summary["candidates_matched"] == 1
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert summary["staking_logic_enabled"] is False
    assert summary["roi_logic_enabled"] is False
    table = pd.read_csv(summary["gate_matrix_output_path"])
    assert table["gate_id"].nunique() >= 19
    assert table.loc[table["gate_id"] == "no_bet_safety_gate", "gate_status"].iloc[0] == DIAGNOSTIC_GATE_DISABLED_NO_BETTING
    assert DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE in set(table["gate_status"])
    assert Path(str(summary["manifest_path"])).exists()
    assert Path(str(summary["summary_path"])).exists()


def test_gate_matrix_builds_when_synthesis_omitted(tmp_path: Path) -> None:
    summary = build_v19_diagnostic_gate_matrix_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
    )
    assert summary["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert summary["gates_evaluated"] >= 19


def test_gate_matrix_selection_modes(tmp_path: Path) -> None:
    synthesis = _synthesis(tmp_path)
    common = {
        "v19_diagnostic_synthesis_path": synthesis["output_path"],
        "output_dir": tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        "base_dir": tmp_path,
        "build_missing": False,
    }
    assert build_v19_diagnostic_gate_matrix_preview(cross_provider_match_key="u-bundesliga-2024-001", **common)["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert build_v19_diagnostic_gate_matrix_preview(understat_provider_match_id="u-bundesliga-2024-001", **common)["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert build_v19_diagnostic_gate_matrix_preview(fbref_provider_match_id="fbref-bundesliga-2024-001", **common)["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert build_v19_diagnostic_gate_matrix_preview(home_team="Home FC", away_team="Away FC", match_date="2024-08-23", competition="Bundesliga", season="2024", **common)["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY


def test_gate_matrix_blocks_missing_unknown_ambiguous_and_unsafe(tmp_path: Path) -> None:
    missing = V19DiagnosticGateMatrixRunner(V19DiagnosticGateMatrixConfig(
        v19_diagnostic_synthesis_path=tmp_path / "missing.csv",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
    )).run()[0]
    assert missing.v19_diagnostic_gate_matrix_status == V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_INPUT

    synthesis = _synthesis(tmp_path)
    unknown = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=synthesis["output_path"],
        cross_provider_match_key="missing",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert unknown["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNKNOWN_MATCH

    frame = pd.read_csv(synthesis["output_path"])
    ambiguous_path = tmp_path / "ambiguous_synthesis.csv"
    pd.concat([frame, frame], ignore_index=True).to_csv(ambiguous_path, index=False)
    ambiguous = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=ambiguous_path,
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert ambiguous["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_AMBIGUOUS_MATCH

    unsafe = V19DiagnosticGateMatrixRunner(V19DiagnosticGateMatrixConfig(
        v19_diagnostic_synthesis_path=synthesis["output_path"],
        output_dir=tmp_path / "data" / "processed",
        base_dir=tmp_path,
    )).run()[0]
    assert unsafe.v19_diagnostic_gate_matrix_status == V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_UNSAFE_PATH


def test_gate_matrix_blocks_missing_columns_and_identity_values(tmp_path: Path) -> None:
    synthesis = _synthesis(tmp_path)
    broken_columns = tmp_path / "broken_columns.csv"
    pd.read_csv(synthesis["output_path"]).drop(columns=["home_team"]).to_csv(broken_columns, index=False)
    missing_columns = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=broken_columns,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert missing_columns["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_COLUMNS

    broken_values = tmp_path / "broken_values.csv"
    frame = pd.read_csv(synthesis["output_path"])
    frame.loc[0, "home_team"] = ""
    frame.to_csv(broken_values, index=False)
    missing_values = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=broken_values,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert missing_values["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_BLOCKED_MISSING_REQUIRED_VALUES


def test_missing_optional_values_are_surfaced_not_inferred(tmp_path: Path) -> None:
    synthesis = _synthesis(tmp_path, "u-bundesliga-2024-002")
    summary = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=synthesis["output_path"],
        cross_provider_match_key="u-bundesliga-2024-002",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert summary["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert summary["missing_optional_fields_count"] >= 1


def test_24_block_report_integrates_gate_matrix_sections(tmp_path: Path) -> None:
    human_input = _human_input(tmp_path)
    synthesis = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=human_input,
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
        base_dir=tmp_path,
        build_missing=False,
    )
    matrix = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=synthesis["output_path"],
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
        base_dir=tmp_path,
        build_missing=False,
    )
    report = build_human_24_block_report_preview(
        context_human_input_path=human_input,
        v19_diagnostic_synthesis_path=synthesis["output_path"],
        v19_diagnostic_gate_matrix_path=matrix["gate_matrix_output_path"],
        output_dir=tmp_path / "outputs" / "analysis_preview" / "human_24_block_report",
        base_dir=tmp_path,
        build_missing=False,
    )
    assert report["sections_rendered"] == 24
    assert report["required_sections_rendered"] == 24
    assert report["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    text = Path(str(report["report_output_path"])).read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert f"## {section}" in text
    assert "Gate matrix diagnostics:" in text
    assert "Betting output is disabled in this diagnostic gate preview layer." in text
    assert "Production prediction logic is disabled by design." in text
    assert "stake size" not in text.lower()
    assert " units" not in text.lower()
    assert "roi" not in text.lower()
    assert "super_a" not in text.lower()


def test_match_analysis_runner_includes_gate_matrix_statuses(tmp_path: Path) -> None:
    summary = build_match_analysis_runner_preview(
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_analysis_runner",
        base_dir=tmp_path,
    )
    assert summary["match_analysis_runner_status"] == "MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    assert summary["v19_diagnostic_synthesis_status"] == V19_DIAGNOSTIC_SYNTHESIS_PREVIEW_READY
    assert summary["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert summary["gates_evaluated"] >= 19
    manifest = pd.read_csv(summary["manifest_path"])
    assert "v19_diagnostic_gate_matrix_status" in manifest.columns
    assert int(manifest["gates_evaluated"].iloc[0]) >= 19


def test_helper_and_audit_return_ready(tmp_path: Path) -> None:
    helper = run_workflow(tmp_path)
    assert helper["recommendation"] == V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW_READY
    assert helper["v19_diagnostic_gate_matrix_status"] == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    assert helper["gates_evaluated"] >= 19
    assert helper["sections_rendered"] == 24
    assert helper["required_sections_rendered"] == 24
    assert helper["network_calls_enabled"] is False
    assert helper["prediction_logic_enabled"] is False
    assert helper["betting_logic_enabled"] is False
    assert helper["staking_logic_enabled"] is False
    assert helper["roi_logic_enabled"] is False

    table, _markdown, rec = run_audit(
        gate_matrix_manifest=helper["gate_matrix_manifest_path"],
        report_manifest=helper["report_manifest_path"],
        output_dir=tmp_path / "outputs" / "diagnostics",
        base_dir=tmp_path,
    )
    assert rec == V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])


def test_no_protected_logic_files_are_modified(tmp_path: Path) -> None:
    before = _hashes()
    helper = run_workflow(tmp_path)
    assert helper["recommendation"] == V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW_READY
    _assert_hashes_unchanged(before)
