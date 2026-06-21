# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from scripts.audit_match_context_bundle_preview import run as run_bundle_audit
from scripts.build_fbref_provider_pull_preview import build_fbref_provider_pull_preview
from scripts.build_match_context_bundle_preview import build_match_context_bundle_preview
from scripts.build_match_context_bundle_preview_helper import run_workflow as run_bundle_helper
from scripts.build_understat_real_snapshot_smoke_preview import build_understat_real_snapshot_smoke_preview
from football_prediction_v19.analysis.match_context_bundle_preview import (
    BUNDLE_COLUMNS,
    MANIFEST_COLUMNS,
    MATCH_CONTEXT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH,
    MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_FBREF_INPUT,
    MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS,
    MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES,
    MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_UNDERSTAT_INPUT,
    MATCH_CONTEXT_BUNDLE_BLOCKED_UNKNOWN_MATCH,
    MATCH_CONTEXT_BUNDLE_BLOCKED_UNSAFE_PATH,
    MATCH_CONTEXT_BUNDLE_OPTIONAL_VALUES_MISSING,
    MATCH_CONTEXT_BUNDLE_PREVIEW_READY,
    MatchContextBundleConfig,
    MatchContextBundleRunner,
)

ROOT = Path(__file__).resolve().parents[1]
UNDERSTAT_FIXTURE = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"
FBREF_FIXTURE = ROOT / "tests" / "fixtures" / "fbref" / "fbref_bundesliga_2024_fixture.json"
PROTECTED_FILES = [
    ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
    ROOT / "src" / "football_prediction_v19" / "recommended_market.py",
]


def _hashes() -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in PROTECTED_FILES if path.exists()}


def _assert_hashes_unchanged(before: dict[Path, str]) -> None:
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    understat = build_understat_real_snapshot_smoke_preview(local_snapshot=UNDERSTAT_FIXTURE, output_dir=tmp_path / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot", base_dir=tmp_path)
    fbref = build_fbref_provider_pull_preview(local_input=FBREF_FIXTURE, output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path)
    return Path(str(understat["normalized_output_path"])), Path(str(fbref["normalized_output_path"]))


def _build(tmp_path: Path, **kwargs: object) -> dict[str, object]:
    understat, fbref = _inputs(tmp_path)
    return build_match_context_bundle_preview(
        understat_normalized_input=understat,
        fbref_normalized_input=fbref,
        output_dir=tmp_path / "outputs" / "analysis_preview" / "match_context_bundle",
        base_dir=tmp_path,
        build_missing=False,
        **kwargs,
    )


def test_builds_context_bundle_from_deterministic_fixtures(tmp_path: Path) -> None:
    summary = _build(tmp_path, cross_provider_match_key="u-bundesliga-2024-001")
    assert summary["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert summary["rows_joined"] == 1
    assert summary["candidates_matched"] == 1
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    bundle = pd.read_csv(summary["output_path"])
    assert set(BUNDLE_COLUMNS).issubset(bundle.columns)
    assert bundle["home_xg"].astype(str).iloc[0] == "1.82"
    assert bundle["home_possession"].astype(str).iloc[0] == "56"


def test_builds_context_bundle_when_inputs_are_omitted(tmp_path: Path) -> None:
    summary = build_match_context_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "analysis_preview" / "match_context_bundle", base_dir=tmp_path)
    assert summary["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert summary["rows_joined"] == 1


def test_join_modes_cross_understat_explicit_ids_and_team_date(tmp_path: Path) -> None:
    assert _build(tmp_path, cross_provider_match_key="u-bundesliga-2024-001")["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert _build(tmp_path, understat_provider_match_id="u-bundesliga-2024-001")["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert _build(tmp_path, understat_provider_match_id="u-bundesliga-2024-001", fbref_provider_match_id="fbref-bundesliga-2024-001")["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert _build(tmp_path, home_team="Home FC", away_team="Away FC", match_date="2024-08-23")["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY


def test_alias_registry_and_competition_season_filters(tmp_path: Path) -> None:
    alias = tmp_path / "aliases.csv"
    alias.write_text("canonical_team_name,alias,provider,league,season,notes\nHome FC,The Home,understat,Bundesliga,2024,test\nAway FC,The Away,understat,Bundesliga,2024,test\nHome FC,The Home,fbref,Bundesliga,2024,test\nAway FC,The Away,fbref,Bundesliga,2024,test\n", encoding="utf-8")
    summary = _build(tmp_path, home_team="The Home", away_team="The Away", match_date="2024-08-23", competition="Bundesliga", season="2024", alias_registry=alias)
    assert summary["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY


def test_blocks_missing_inputs_unknown_ambiguous_missing_columns_and_values(tmp_path: Path) -> None:
    understat, fbref = _inputs(tmp_path)
    out = tmp_path / "outputs" / "analysis_preview" / "match_context_bundle"

    missing_understat = MatchContextBundleRunner(MatchContextBundleConfig(understat_normalized_input=tmp_path / "missing_understat.csv", fbref_normalized_input=fbref, output_dir=out, base_dir=tmp_path)).run()[0]
    assert missing_understat.context_bundle_status == MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_UNDERSTAT_INPUT

    missing_fbref = MatchContextBundleRunner(MatchContextBundleConfig(understat_normalized_input=understat, fbref_normalized_input=tmp_path / "missing_fbref.csv", output_dir=out, base_dir=tmp_path)).run()[0]
    assert missing_fbref.context_bundle_status == MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_FBREF_INPUT

    unknown = _build(tmp_path, cross_provider_match_key="missing")
    assert unknown["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_BLOCKED_UNKNOWN_MATCH

    ambiguous = _build(tmp_path)
    assert ambiguous["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH

    broken = tmp_path / "broken_understat.csv"
    pd.read_csv(understat).drop(columns=["home_team"]).to_csv(broken, index=False)
    missing_columns = build_match_context_bundle_preview(understat_normalized_input=broken, fbref_normalized_input=fbref, output_dir=out, base_dir=tmp_path, build_missing=False)
    assert missing_columns["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS

    missing_values_path = tmp_path / "missing_values_understat.csv"
    frame = pd.read_csv(understat)
    frame.loc[0, "home_team"] = ""
    frame.to_csv(missing_values_path, index=False)
    missing_values = build_match_context_bundle_preview(understat_normalized_input=missing_values_path, fbref_normalized_input=fbref, cross_provider_match_key="u-bundesliga-2024-001", output_dir=out, base_dir=tmp_path, build_missing=False)
    assert missing_values["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES


def test_blocks_unsafe_output_and_input_paths(tmp_path: Path) -> None:
    understat, fbref = _inputs(tmp_path)
    unsafe_out = MatchContextBundleRunner(MatchContextBundleConfig(understat_normalized_input=understat, fbref_normalized_input=fbref, cross_provider_match_key="u-bundesliga-2024-001", output_dir=tmp_path / "data" / "processed", base_dir=tmp_path)).run()[0]
    assert unsafe_out.context_bundle_status == MATCH_CONTEXT_BUNDLE_BLOCKED_UNSAFE_PATH
    unsafe_input = MatchContextBundleRunner(MatchContextBundleConfig(understat_normalized_input=tmp_path / "data" / "processed" / "input.csv", fbref_normalized_input=fbref, output_dir=tmp_path / "outputs" / "analysis_preview" / "match_context_bundle", base_dir=tmp_path)).run()[0]
    assert unsafe_input.context_bundle_status == MATCH_CONTEXT_BUNDLE_BLOCKED_UNSAFE_PATH


def test_missing_optional_fields_are_surfaced_not_inferred(tmp_path: Path) -> None:
    summary = _build(tmp_path, cross_provider_match_key="u-bundesliga-2024-002")
    assert summary["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert summary["missing_optional_fields_count"] >= 1
    bundle = pd.read_csv(summary["output_path"])
    assert bundle["normalization_warning"].astype(str).str.contains(MATCH_CONTEXT_BUNDLE_OPTIONAL_VALUES_MISSING).any()
    assert bundle["away_clearances"].fillna("").iloc[0] == ""


def test_writes_bundle_manifest_markdown_audit_and_helper(tmp_path: Path) -> None:
    summary = _build(tmp_path, cross_provider_match_key="u-bundesliga-2024-001")
    assert Path(str(summary["output_path"])).exists()
    assert Path(str(summary["manifest_path"])).exists()
    assert Path(str(summary["summary_path"])).exists()
    manifest = pd.read_csv(summary["manifest_path"])
    assert set(MANIFEST_COLUMNS).issubset(manifest.columns)

    table, _markdown, rec = run_bundle_audit(manifest=summary["manifest_path"], output_dir=tmp_path / "outputs" / "diagnostics", base_dir=tmp_path)
    assert rec == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])

    helper = run_bundle_helper(tmp_path)
    assert helper["context_bundle_status"] == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    assert helper["understat_status"] == "UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY"
    assert helper["fbref_provider_pull_status"] == "FBREF_PROVIDER_PULL_PREVIEW_READY"
    assert helper["fbref_match_finder_status"] == "FBREF_MATCH_FINDER_PREVIEW_READY"
    assert helper["rows_joined"] == 1
    assert helper["candidates_matched"] == 1
    assert helper["network_calls_enabled"] is False
    assert helper["prediction_logic_enabled"] is False
    assert helper["betting_logic_enabled"] is False


def test_no_protected_logic_files_are_modified(tmp_path: Path) -> None:
    before = _hashes()
    _build(tmp_path, cross_provider_match_key="u-bundesliga-2024-001")
    _assert_hashes_unchanged(before)
