from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_understat_real_snapshot_smoke_preview as audit_smoke  # noqa: E402
import build_provider_to_human_bundle_from_understat_real_snapshot_preview as real_bundle  # noqa: E402
import build_understat_real_snapshot_smoke_preview as build_smoke  # noqa: E402
import build_understat_real_snapshot_smoke_preview_helper as helper  # noqa: E402
from football_prediction_v19.importers.understat_real_snapshot_smoke_preview import (  # noqa: E402
    MANIFEST_COLUMNS,
    UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_REQUIRED_COLUMNS,
    UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_PARSE_ERROR,
    UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_UNSAFE_PATH,
    UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY,
    UNDERSTAT_REAL_SNAPSHOT_SMOKE_OPTIONAL_VALUES_MISSING,
    UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY,
    UnderstatRealSnapshotSmokeConfig,
    UnderstatRealSnapshotSmokeRunner,
)

FIXTURE = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(root: Path, **kwargs):
    output_dir = kwargs.pop("output_dir", root / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot")
    return build_smoke.build_understat_real_snapshot_smoke_preview(output_dir=output_dir, base_dir=root, **kwargs)


def test_default_mode_does_not_perform_network_calls(tmp_path):
    summary = _build(tmp_path / "repo")

    assert summary["real_snapshot_status"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY
    assert summary["network_calls_enabled"] is False
    assert summary["recommendation"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY


def test_allow_network_is_required_for_live_fetch_path(tmp_path):
    calls = []

    def fetcher(_league, _season):
        calls.append("fetch")
        return FIXTURE.read_text(encoding="utf-8")

    result, _frame = UnderstatRealSnapshotSmokeRunner(UnderstatRealSnapshotSmokeConfig(base_dir=tmp_path / "repo", fetcher=fetcher)).run()

    assert result.real_snapshot_status == UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY
    assert calls == []


def test_mocked_live_fetch_writes_raw_normalized_and_manifest(tmp_path):
    root = tmp_path / "repo"

    def fetcher(_league, _season):
        return FIXTURE.read_text(encoding="utf-8")

    result, frame = UnderstatRealSnapshotSmokeRunner(UnderstatRealSnapshotSmokeConfig(output_dir=root / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot", base_dir=root, allow_network=True, fetcher=fetcher)).run()

    assert result.real_snapshot_status == UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY
    assert result.network_calls_enabled is True
    assert len(frame) == 2
    assert Path(result.raw_snapshot_path).exists()
    assert Path(result.normalized_output_path).exists()
    assert Path(result.manifest_path).exists()


def test_local_snapshot_reads_without_network_and_normalizes_rows(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root, local_snapshot=FIXTURE)

    assert summary["real_snapshot_status"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY
    assert summary["network_calls_enabled"] is False
    assert summary["rows_normalized"] == 2


def test_blocks_unsafe_output_and_snapshot_input_paths(tmp_path):
    root = tmp_path / "repo"
    unsafe_output = _build(root, local_snapshot=FIXTURE, output_dir=root / "outputs" / "not_real_snapshot")
    protected = root / "data" / "processed" / "understat.json"
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    unsafe_input = _build(root, local_snapshot=protected)

    assert unsafe_output["real_snapshot_status"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_UNSAFE_PATH
    assert unsafe_input["real_snapshot_status"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_UNSAFE_PATH


def test_blocks_parse_errors_and_missing_required_fields(tmp_path):
    root = tmp_path / "repo"
    bad = root / "bad.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{bad", encoding="utf-8")
    missing = root / "missing.json"
    missing.write_text(json.dumps({"matches": [{"id": "m1"}]}), encoding="utf-8")

    bad_summary = _build(root, local_snapshot=bad)
    missing_summary = _build(root, local_snapshot=missing)

    assert bad_summary["real_snapshot_status"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_PARSE_ERROR
    assert missing_summary["real_snapshot_status"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_REQUIRED_COLUMNS


def test_missing_optional_values_are_surfaced_not_inferred(tmp_path):
    root = tmp_path / "repo"
    fixture = root / "optional_missing.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps({"matches": [{"id": "m1", "date": "2024-08-23", "h": {"title": "A"}, "a": {"title": "B"}, "goals": {"h": "1", "a": "0"}, "xG": {"h": "0.8", "a": "0.4"}}]}), encoding="utf-8")

    summary = _build(root, local_snapshot=fixture)
    frame = pd.read_csv(summary["normalized_output_path"], low_memory=False)

    assert summary["rows_with_missing_optional_values"] == 1
    assert UNDERSTAT_REAL_SNAPSHOT_SMOKE_OPTIONAL_VALUES_MISSING in summary["notes"]
    assert "venue" in frame.iloc[0]["normalization_warning"]


def test_manifest_columns_and_output_paths_are_under_real_snapshot(tmp_path):
    root = tmp_path / "repo"
    summary = _build(root, local_snapshot=FIXTURE)
    manifest = pd.read_csv(summary["manifest_path"], low_memory=False)

    assert set(MANIFEST_COLUMNS).issubset(manifest.columns)
    for key, rel in [("raw_snapshot_path", "raw"), ("normalized_output_path", "normalized"), ("manifest_path", "")]:
        path = Path(summary[key]).resolve()
        allowed = (root / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot" / rel).resolve()
        assert path == allowed or allowed in path.parents or path.parent == allowed


def test_audit_and_helper_return_ready(tmp_path):
    root = tmp_path / "repo"

    table, _md, rec = audit_smoke.run(output_dir=root / "outputs" / "diagnostics", base_dir=root)
    helper_summary = helper.run_workflow(root)

    assert rec == UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY
    assert bool(table.iloc[0]["preview_valid"])
    assert helper_summary["understat_real_snapshot_smoke_status"] == UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY
    assert helper_summary["network_calls_enabled"] is False


def test_real_snapshot_bundle_blocks_missing_input_and_runs_with_local_normalized_input(tmp_path):
    root = tmp_path / "repo"
    missing = real_bundle.build_bundle_from_real_snapshot(base_dir=root, output_dir=root / "outputs" / "analysis_preview" / "provider_to_human_real_snapshot_bundle")
    smoke = _build(root, local_snapshot=FIXTURE)
    built = real_bundle.build_bundle_from_real_snapshot(normalized_input=smoke["normalized_output_path"], provider_match_id="u-bundesliga-2024-001", base_dir=root, output_dir=root / "outputs" / "analysis_preview" / "provider_to_human_real_snapshot_bundle")

    assert missing["real_snapshot_bundle_status"] == real_bundle.PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MISSING_NORMALIZED_INPUT
    assert built["real_snapshot_bundle_status"] == real_bundle.PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_READY
    assert built["human_match_pipeline_status"] == "HUMAN_MATCH_PIPELINE_PREVIEW_READY"
    assert built["rows_reported"] == 1
    assert built["steps_failed"] == 0
    assert built["network_calls_enabled"] is False


def test_no_external_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text


def test_no_production_or_protected_files_modified(tmp_path):
    root = tmp_path / "repo"
    protected = [
        root / "data" / "processed" / "target_clean.csv",
        root / "data" / "trusted_xg_sources" / "accepted" / "accepted_xg.csv",
        root / "data" / "trusted_xg_sources" / "raw" / "raw_source.csv",
        root / "data" / "templates" / "manual_xg_manifest_template.csv",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    for path in protected[:4]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sentinel\n", encoding="utf-8")
    before = {path: _sha(path) for path in protected if path.exists()}

    helper.run_workflow(root)

    assert {path: _sha(path) for path in protected if path.exists()} == before
