# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from scripts.audit_fbref_match_finder_preview import run as run_match_finder_audit
from scripts.audit_fbref_provider_pull_preview import run as run_provider_audit
from scripts.build_fbref_match_finder_preview_helper import run_workflow as run_match_finder_helper
from scripts.build_fbref_provider_pull_preview import build_fbref_provider_pull_preview
from scripts.build_fbref_provider_pull_preview_helper import run_workflow as run_provider_helper
from scripts.find_fbref_match_preview import find_fbref_match_preview
from football_prediction_v19.importers.fbref_match_finder_preview import (
    FBREF_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH,
    FBREF_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT,
    FBREF_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS,
    FBREF_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH,
    FBREF_MATCH_FINDER_BLOCKED_UNSAFE_PATH,
    FBREF_MATCH_FINDER_PREVIEW_READY,
    FBrefMatchFinderConfig,
    FBrefMatchFinderPreviewRunner,
    MANIFEST_COLUMNS as MATCH_FINDER_MANIFEST_COLUMNS,
)
from football_prediction_v19.importers.fbref_provider_pull_preview import (
    FBREF_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT,
    FBREF_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS,
    FBREF_PROVIDER_PULL_BLOCKED_PARSE_ERROR,
    FBREF_PROVIDER_PULL_BLOCKED_UNSAFE_PATH,
    FBREF_PROVIDER_PULL_OPTIONAL_VALUES_MISSING,
    FBREF_PROVIDER_PULL_PREVIEW_READY,
    FBrefProviderPullConfig,
    FBrefProviderPullPreviewRunner,
    MANIFEST_COLUMNS as PROVIDER_MANIFEST_COLUMNS,
    NORMALIZED_COLUMNS,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "fbref" / "fbref_bundesliga_2024_fixture.json"
PROTECTED_FILES = [
    ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
    ROOT / "src" / "football_prediction_v19" / "recommended_market.py",
]


def _hashes() -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in PROTECTED_FILES if path.exists()}


def _assert_hashes_unchanged(before: dict[Path, str]) -> None:
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def _build_provider(tmp_path: Path, **kwargs: object) -> dict[str, object]:
    return build_fbref_provider_pull_preview(output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path, **kwargs)


def _normalized(tmp_path: Path) -> Path:
    summary = _build_provider(tmp_path, local_input=FIXTURE)
    return Path(str(summary["normalized_output_path"]))


def test_builds_fbref_provider_pull_preview_from_local_fixture(tmp_path: Path) -> None:
    summary = _build_provider(tmp_path, local_input=FIXTURE)
    assert summary["fbref_provider_pull_status"] == FBREF_PROVIDER_PULL_PREVIEW_READY
    assert summary["provider"] == "fbref"
    assert summary["competition"] == "Bundesliga"
    assert summary["season"] == "2024"
    assert summary["rows_normalized"] == 2
    assert summary["network_calls_enabled"] is False
    assert summary["recommendation"] == FBREF_PROVIDER_PULL_PREVIEW_READY


def test_default_mode_uses_fixture_and_does_not_fetch_network(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fetcher(competition: str, season: str) -> str:
        calls.append((competition, season))
        return "{}"

    result, _frame = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path, fetcher=fetcher)).run()
    assert result.fbref_provider_pull_status == FBREF_PROVIDER_PULL_PREVIEW_READY
    assert result.network_calls_enabled is False
    assert calls == []


def test_allow_network_is_required_for_live_fetch_path(tmp_path: Path) -> None:
    result, _frame = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(local_input=tmp_path / "missing.json", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path)).run()
    assert result.fbref_provider_pull_status == FBREF_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT
    assert result.network_calls_enabled is False


def test_mocked_live_fetch_path_writes_raw_normalized_and_manifest(tmp_path: Path) -> None:
    def fetcher(_competition: str, _season: str) -> str:
        return FIXTURE.read_text(encoding="utf-8")

    result, frame = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(allow_network=True, fetcher=fetcher, output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path)).run()
    assert result.fbref_provider_pull_status == FBREF_PROVIDER_PULL_PREVIEW_READY
    assert result.network_calls_enabled is True
    assert Path(result.raw_output_path).exists()
    assert Path(result.normalized_output_path).exists()
    assert Path(result.manifest_path).exists()
    assert len(frame) == 2


def test_local_fixture_normalizes_rows_and_surfaces_optional_missing_values(tmp_path: Path) -> None:
    summary = _build_provider(tmp_path, local_input=FIXTURE)
    frame = pd.read_csv(summary["normalized_output_path"])
    assert set(NORMALIZED_COLUMNS).issubset(frame.columns)
    assert summary["rows_with_missing_optional_values"] >= 1
    assert frame["normalization_warning"].astype(str).str.contains(FBREF_PROVIDER_PULL_OPTIONAL_VALUES_MISSING).any()
    assert frame.loc[frame["provider_match_id"] == "fbref-bundesliga-2024-002", "away_clearances"].fillna("").iloc[0] == ""


def test_provider_blocks_unsafe_paths_parse_errors_and_missing_identity(tmp_path: Path) -> None:
    unsafe_out, _ = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(local_input=FIXTURE, output_dir=tmp_path / "data" / "processed", base_dir=tmp_path)).run()
    assert unsafe_out.fbref_provider_pull_status == FBREF_PROVIDER_PULL_BLOCKED_UNSAFE_PATH

    unsafe_local, _ = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(local_input=tmp_path / "data" / "processed" / "fixture.json", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path)).run()
    assert unsafe_local.fbref_provider_pull_status == FBREF_PROVIDER_PULL_BLOCKED_UNSAFE_PATH

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not-json", encoding="utf-8")
    bad_result, _ = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(local_input=bad_json, output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path)).run()
    assert bad_result.fbref_provider_pull_status == FBREF_PROVIDER_PULL_BLOCKED_PARSE_ERROR

    missing_required = tmp_path / "missing_required.json"
    missing_required.write_text(json.dumps({"matches": [{"provider_match_id": "x"}]}), encoding="utf-8")
    missing_result, _ = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(local_input=missing_required, output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref", base_dir=tmp_path)).run()
    assert missing_result.fbref_provider_pull_status == FBREF_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS


def test_provider_manifest_columns_paths_audit_and_helper(tmp_path: Path) -> None:
    summary = _build_provider(tmp_path, local_input=FIXTURE)
    manifest = pd.read_csv(summary["manifest_path"])
    assert set(PROVIDER_MANIFEST_COLUMNS).issubset(manifest.columns)
    assert str(summary["normalized_output_path"]).replace("\\", "/").endswith("outputs/provider_pull_preview/fbref/normalized/fbref_provider_pull_normalized.csv")

    table, _markdown, rec = run_provider_audit(manifest=summary["manifest_path"], output_dir=tmp_path / "outputs" / "diagnostics", base_dir=tmp_path)
    assert rec == FBREF_PROVIDER_PULL_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])

    helper = run_provider_helper(tmp_path / "outputs" / "provider_pull_preview" / "fbref")
    assert helper["fbref_provider_pull_status"] == FBREF_PROVIDER_PULL_PREVIEW_READY
    assert helper["network_calls_enabled"] is False


def test_finds_fbref_match_by_provider_and_understat_ids(tmp_path: Path) -> None:
    normalized = _normalized(tmp_path)
    by_provider = find_fbref_match_preview(normalized_input=normalized, provider_match_id="fbref-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert by_provider["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY
    assert by_provider["candidates_matched"] == 1

    by_understat = find_fbref_match_preview(normalized_input=normalized, understat_provider_match_id="u-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert by_understat["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY
    assert by_understat["provider_match_id"] == "fbref-bundesliga-2024-001"


def test_finds_fbref_match_by_exact_normalized_and_alias_team_names(tmp_path: Path) -> None:
    normalized = _normalized(tmp_path)
    exact = find_fbref_match_preview(normalized_input=normalized, home_team="Home FC", away_team="Away FC", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert exact["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY

    normalized_names = find_fbref_match_preview(normalized_input=normalized, home_team="home-f.c.", away_team="away   fc", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert normalized_names["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY
    assert normalized_names["alias_match_used"] is False

    alias = tmp_path / "aliases.csv"
    alias.write_text("canonical_team_name,alias,provider,league,season,notes\nHome FC,The Home,fbref,Bundesliga,2024,test\nAway FC,The Away,fbref,Bundesliga,2024,test\n", encoding="utf-8")
    alias_result = find_fbref_match_preview(normalized_input=normalized, home_team="The Home", away_team="The Away", competition="Bundesliga", season="2024", alias_registry=alias, output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert alias_result["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY
    assert alias_result["alias_match_used"] is True


def test_finder_supports_date_competition_and_season_filters(tmp_path: Path) -> None:
    normalized = _normalized(tmp_path)
    result = find_fbref_match_preview(normalized_input=normalized, home_team="Home FC", away_team="Away FC", match_date="2024-08-23", competition="Bundesliga", season="2024", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert result["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY
    assert result["match_date"] == "2024-08-23"


def test_finder_blocks_unknown_ambiguous_missing_input_missing_columns_and_unsafe_paths(tmp_path: Path) -> None:
    normalized = _normalized(tmp_path)
    unknown = find_fbref_match_preview(normalized_input=normalized, provider_match_id="missing", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert unknown["fbref_match_finder_status"] == FBREF_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH

    ambiguous = find_fbref_match_preview(normalized_input=normalized, competition="Bundesliga", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert ambiguous["fbref_match_finder_status"] == FBREF_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH

    missing = find_fbref_match_preview(normalized_input=tmp_path / "missing.csv", provider_match_id="fbref-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert missing["fbref_match_finder_status"] == FBREF_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT

    broken = tmp_path / "broken.csv"
    pd.read_csv(normalized).drop(columns=["home_team"]).to_csv(broken, index=False)
    missing_columns = find_fbref_match_preview(normalized_input=broken, provider_match_id="fbref-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert missing_columns["fbref_match_finder_status"] == FBREF_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS

    unsafe = FBrefMatchFinderPreviewRunner(FBrefMatchFinderConfig(normalized_input=normalized, provider_match_id="fbref-bundesliga-2024-001", output_dir=tmp_path / "data" / "processed", base_dir=tmp_path)).run()[0]
    assert unsafe.fbref_match_finder_status == FBREF_MATCH_FINDER_BLOCKED_UNSAFE_PATH


def test_finder_writes_outputs_and_keeps_optional_missing_values_blank(tmp_path: Path) -> None:
    normalized = _normalized(tmp_path)
    result = find_fbref_match_preview(normalized_input=normalized, provider_match_id="fbref-bundesliga-2024-002", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    assert result["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY
    selected = pd.read_csv(result["selected_match_output_path"])
    manifest = pd.read_csv(result["manifest_path"])
    assert set(MATCH_FINDER_MANIFEST_COLUMNS).issubset(manifest.columns)
    assert Path(str(result["summary_path"])).exists()
    assert selected["away_clearances"].fillna("").iloc[0] == ""
    assert result["network_calls_enabled"] is False
    assert result["prediction_logic_enabled"] is False
    assert result["betting_logic_enabled"] is False


def test_match_finder_audit_and_helper_return_ready(tmp_path: Path) -> None:
    normalized = _normalized(tmp_path)
    result = find_fbref_match_preview(normalized_input=normalized, provider_match_id="fbref-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    table, _markdown, rec = run_match_finder_audit(manifest=result["manifest_path"], output_dir=tmp_path / "outputs" / "diagnostics", base_dir=tmp_path)
    assert rec == FBREF_MATCH_FINDER_PREVIEW_READY
    assert bool(table["preview_valid"].iloc[0])

    helper = run_match_finder_helper(tmp_path)
    assert helper["fbref_provider_pull_status"] == FBREF_PROVIDER_PULL_PREVIEW_READY
    assert helper["fbref_match_finder_status"] == FBREF_MATCH_FINDER_PREVIEW_READY
    assert helper["candidates_matched"] == 1
    assert helper["network_calls_enabled"] is False
    assert helper["prediction_logic_enabled"] is False
    assert helper["betting_logic_enabled"] is False


def test_phase19_does_not_modify_protected_logic_files(tmp_path: Path) -> None:
    before = _hashes()
    normalized = _normalized(tmp_path)
    find_fbref_match_preview(normalized_input=normalized, provider_match_id="fbref-bundesliga-2024-001", output_dir=tmp_path / "outputs" / "provider_pull_preview" / "fbref" / "match_finder", base_dir=tmp_path, build_missing=False)
    _assert_hashes_unchanged(before)
