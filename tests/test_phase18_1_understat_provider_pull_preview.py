from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_understat_provider_pull_preview as audit_understat  # noqa: E402
import build_human_match_pipeline_from_manual_input_preview as pipeline_from_manual  # noqa: E402
import build_manual_input_from_understat_provider_pull_preview as bridge_script  # noqa: E402
import build_understat_provider_pull_preview as build_understat  # noqa: E402
import build_understat_provider_pull_preview_helper as helper  # noqa: E402
import validate_manual_human_match_input as validate_manual  # noqa: E402
from football_prediction_v19.importers.understat_provider_pull_preview import (  # noqa: E402
    MANIFEST_COLUMNS,
    NORMALIZED_COLUMNS,
    UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT,
    UNDERSTAT_PROVIDER_PULL_BLOCKED_PARSE_ERROR,
    UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH,
    UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING,
    UNDERSTAT_PROVIDER_PULL_PREVIEW_PARTIAL_READY,
    UNDERSTAT_PROVIDER_PULL_PREVIEW_READY,
    UnderstatProviderPullConfig,
    UnderstatProviderPuller,
)


FIXTURE = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(root: Path) -> dict[str, object]:
    return build_understat.build_understat_provider_pull_preview(
        league="Bundesliga",
        season="2024",
        input_path=FIXTURE,
        output_dir=root / "outputs" / "provider_pull_preview" / "understat",
        allow_network=False,
        write_preview=True,
        base_dir=root,
    )


def test_builds_understat_provider_pull_preview_from_local_fixture(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root)

    assert summary["provider_pull_status"] == UNDERSTAT_PROVIDER_PULL_PREVIEW_READY
    assert summary["provider"] == "understat"
    assert summary["network_calls_enabled"] is False
    assert summary["rows_normalized"] == 2
    assert Path(summary["normalized_output_path"]).exists()
    assert Path(summary["raw_snapshot_path"]).exists()
    assert Path(summary["manifest_path"]).exists()


def test_blocks_network_by_default_when_no_local_input_is_provided(tmp_path):
    root = tmp_path / "repo"

    summary = build_understat.build_understat_provider_pull_preview(
        league="Bundesliga",
        season="2024",
        output_dir=root / "outputs" / "provider_pull_preview" / "understat",
        allow_network=False,
        base_dir=root,
    )

    assert summary["provider_pull_status"] == UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT
    assert summary["network_calls_enabled"] is False


def test_allow_network_flag_is_required_for_real_provider_pull_path(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    calls: list[str] = []

    def fake_fetch(self):
        calls.append("called")
        return FIXTURE.read_text(encoding="utf-8")

    monkeypatch.setattr(UnderstatProviderPuller, "_fetch_remote", fake_fetch)

    blocked = build_understat.build_understat_provider_pull_preview(
        league="Bundesliga",
        season="2024",
        output_dir=root / "outputs" / "provider_pull_preview" / "understat",
        allow_network=False,
        base_dir=root,
    )
    allowed = build_understat.build_understat_provider_pull_preview(
        league="Bundesliga",
        season="2024",
        output_dir=root / "outputs" / "provider_pull_preview" / "understat",
        allow_network=True,
        base_dir=root,
    )

    assert blocked["provider_pull_status"] == UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT
    assert allowed["network_calls_enabled"] is True
    assert calls == ["called"]


def test_parses_fixture_into_normalized_rows(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root)
    frame = pd.read_csv(summary["normalized_output_path"], low_memory=False)

    assert list(frame.columns) == NORMALIZED_COLUMNS
    assert frame.iloc[0]["provider_match_id"] == "u-bundesliga-2024-001"
    assert float(frame.iloc[0]["home_xg"]) == 1.82
    assert float(frame.iloc[0]["away_xga"]) == 1.82


def test_writes_raw_normalized_and_manifest_under_provider_preview_dirs(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root)

    for key, rel in [
        ("raw_snapshot_path", "outputs/provider_pull_preview/understat/raw"),
        ("normalized_output_path", "outputs/provider_pull_preview/understat/normalized"),
        ("manifest_path", "outputs/provider_pull_preview/understat"),
    ]:
        path = Path(summary[key]).resolve()
        assert (root / rel).resolve() in path.parents or path.parent == (root / rel).resolve()


def test_manifest_required_columns_and_audit_ready(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root)
    manifest = pd.read_csv(summary["manifest_path"], low_memory=False)

    table, _markdown, rec = audit_understat.run(manifest=summary["manifest_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert set(MANIFEST_COLUMNS).issubset(manifest.columns)
    assert rec == UNDERSTAT_PROVIDER_PULL_PREVIEW_READY
    assert bool(table.iloc[0]["preview_valid"])


def test_helper_returns_understat_provider_pull_preview_ready(monkeypatch, tmp_path):
    root = tmp_path / "repo"

    summary = helper.run_workflow(root / "outputs" / "provider_pull_preview" / "understat")

    assert summary["understat_provider_pull_status"] == UNDERSTAT_PROVIDER_PULL_PREVIEW_READY
    assert summary["provider"] == "understat"
    assert summary["network_calls_enabled"] is False


def test_missing_optional_values_are_surfaced_not_inferred(tmp_path):
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    fixture = root / "missing_optional.json"
    fixture.write_text(json.dumps({"matches": [{"id": "m1", "date": "2024-08-23", "h": {"title": "A"}, "a": {"title": "B"}, "goals": {"h": "1", "a": "0"}, "xG": {"h": "0.7", "a": "0.4"}}]}), encoding="utf-8")

    summary = build_understat.build_understat_provider_pull_preview(
        league="Bundesliga",
        season="2024",
        input_path=fixture,
        output_dir=root / "outputs" / "provider_pull_preview" / "understat",
        base_dir=root,
    )
    frame = pd.read_csv(summary["normalized_output_path"], low_memory=False)

    assert summary["provider_pull_status"] == UNDERSTAT_PROVIDER_PULL_PREVIEW_PARTIAL_READY
    assert summary["rows_with_missing_optional_values"] == 1
    assert UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING in frame.iloc[0]["normalization_warning"]


def test_parse_errors_are_blocked(tmp_path):
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    fixture = root / "bad.json"
    fixture.write_text("{bad json", encoding="utf-8")

    result, _frame = UnderstatProviderPuller(
        UnderstatProviderPullConfig(league="Bundesliga", season="2024", input_path=fixture, output_dir=root / "outputs" / "provider_pull_preview" / "understat", base_dir=root)
    ).run()

    assert result.provider_pull_status == UNDERSTAT_PROVIDER_PULL_BLOCKED_PARSE_ERROR


def test_unsafe_output_paths_are_blocked(tmp_path):
    root = tmp_path / "repo"

    summary = build_understat.build_understat_provider_pull_preview(
        league="Bundesliga",
        season="2024",
        input_path=FIXTURE,
        output_dir=root / "outputs" / "not_provider_preview",
        base_dir=root,
    )

    assert summary["provider_pull_status"] == UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH


def test_bridge_converts_normalized_provider_output_into_manual_input_csv(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root)

    bridged = bridge_script.build_manual_input_from_understat_provider_pull_preview(
        normalized_input=summary["normalized_output_path"],
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )
    frame = pd.read_csv(bridged["output_path"], low_memory=False)

    assert bridged["manual_input_bridge_status"] == bridge_script.MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_READY
    assert bridged["rows_written"] == 1
    assert frame.iloc[0]["source_id"] == "understat_provider_pull_preview"


def test_bridge_supports_match_id_selection_and_blocks_unknown_match_id(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root)

    selected = bridge_script.build_manual_input_from_understat_provider_pull_preview(
        normalized_input=summary["normalized_output_path"],
        match_id="u-bundesliga-2024-002",
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )
    missing = bridge_script.build_manual_input_from_understat_provider_pull_preview(
        normalized_input=summary["normalized_output_path"],
        match_id="missing",
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )

    assert selected["provider_match_id"] == "u-bundesliga-2024-002"
    assert missing["manual_input_bridge_status"] == bridge_script.MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_UNKNOWN_MATCH_ID


def test_generated_manual_input_validates_and_runs_human_pipeline(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root)
    bridged = bridge_script.build_manual_input_from_understat_provider_pull_preview(
        normalized_input=summary["normalized_output_path"],
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )

    validation = validate_manual.validate_manual_human_match_input(
        input_path=bridged["output_path"],
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )
    pipeline = pipeline_from_manual.build_pipeline_from_manual_input(
        input_path=bridged["output_path"],
        output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline",
        base_dir=root,
    )

    assert validation["validation_status"] == "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY"
    assert pipeline["human_match_pipeline_status"] == "HUMAN_MATCH_PIPELINE_PREVIEW_READY"


def test_network_prediction_and_betting_flags_disabled_in_fixture_modes(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root)
    bridged = bridge_script.build_manual_input_from_understat_provider_pull_preview(
        normalized_input=summary["normalized_output_path"],
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )

    assert summary["network_calls_enabled"] is False
    assert bridged["network_calls_enabled"] is False
    assert bridged["prediction_logic_enabled"] is False
    assert bridged["betting_logic_enabled"] is False


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root = tmp_path / "repo"
    protected = [
        root / "data" / "processed" / "target_clean.csv",
        root / "data" / "trusted_xg_sources" / "accepted" / "accepted_xg.csv",
        root / "data" / "trusted_xg_sources" / "raw" / "raw_source.csv",
        root / "data" / "templates" / "manual_xg_manifest_template.csv",
    ]
    for path in protected:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sentinel\n", encoding="utf-8")
    before = {path: _sha(path) for path in protected}

    summary = _build(root)
    bridge_script.build_manual_input_from_understat_provider_pull_preview(
        normalized_input=summary["normalized_output_path"],
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )

    assert {path: _sha(path) for path in protected} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}

    _build(tmp_path / "repo")

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_real_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
