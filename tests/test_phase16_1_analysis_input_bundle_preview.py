from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_analysis_input_bundle_preview as bundle_audit  # noqa: E402
import build_analysis_input_bundle_preview as bundle_preview  # noqa: E402
import build_analysis_input_bundle_preview_helper as helper  # noqa: E402
from football_prediction_v19.analysis.input_bundle import (  # noqa: E402
    ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_FILE,
    ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS,
    ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES,
    ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH,
    ANALYSIS_INPUT_BUNDLE_PREVIEW_READY,
    AnalysisInputBundleBuilder,
    AnalysisInputBundleConfig,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_match(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "source_id": "file_csv",
        "provider_match_id": "m1",
        "league": "Preview League",
        "season": "2024",
        "date": "2024-08-23",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "home_goals": 2,
        "away_goals": 1,
        "match_status": "finished",
        "extra_value": "not promoted into bundle",
    }]).to_csv(path, index=False)
    return path


def _build(tmp_path: Path) -> tuple[Path, dict[str, object], pd.DataFrame]:
    root = tmp_path / "repo"
    source = _canonical_match(root / "outputs" / "importer_preview" / "normalized" / "canonical_match_preview.csv")
    summary = bundle_preview.build_analysis_input_bundle_preview(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "input_bundle", write_preview=True, base_dir=root)
    manifest = pd.read_csv(summary["bundle_manifest_path"], low_memory=False)
    return root, summary, manifest


def test_builds_analysis_input_bundle_preview(tmp_path):
    _root, summary, _manifest = _build(tmp_path)

    assert summary["analysis_input_bundle_status"] == ANALYSIS_INPUT_BUNDLE_PREVIEW_READY
    assert summary["rows_input"] == 1
    assert summary["rows_ready"] == 1
    assert Path(summary["bundle_manifest_path"]).exists()


def test_builds_missing_file_based_importer_preview_when_default_missing(tmp_path):
    root = tmp_path / "repo"

    summary = bundle_preview.build_analysis_input_bundle_preview(output_dir=root / "outputs" / "analysis_preview" / "input_bundle", write_preview=True, base_dir=root)

    assert summary["analysis_input_bundle_status"] == ANALYSIS_INPUT_BUNDLE_PREVIEW_READY
    assert (root / "outputs" / "importer_preview" / "normalized" / "canonical_match_preview.csv").exists()


def test_validates_required_canonical_match_columns(tmp_path):
    root = tmp_path / "repo"
    source = _canonical_match(root / "input.csv")

    builder = AnalysisInputBundleBuilder(AnalysisInputBundleConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "input_bundle", base_dir=root))
    result, ready, _validation = builder.build()

    assert result.bundle_status == ANALYSIS_INPUT_BUNDLE_PREVIEW_READY
    assert set(["source_id", "provider_match_id", "league", "season", "date", "home_team", "away_team", "home_goals", "away_goals", "match_status"]) == set(ready.columns)


def test_blocks_missing_input_file_when_build_missing_disabled(tmp_path):
    root = tmp_path / "repo"

    summary = bundle_preview.build_analysis_input_bundle_preview(output_dir=root / "outputs" / "analysis_preview" / "input_bundle", write_preview=True, build_missing_importer_preview=False, base_dir=root)

    assert summary["analysis_input_bundle_status"] == ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_FILE


def test_blocks_missing_required_columns(tmp_path):
    root = tmp_path / "repo"
    source = root / "input.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"source_id": "file_csv", "date": "2024-08-23"}]).to_csv(source, index=False)

    builder = AnalysisInputBundleBuilder(AnalysisInputBundleConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "input_bundle", base_dir=root))
    result, _ready, _validation = builder.build()

    assert result.bundle_status == ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS
    assert "provider_match_id" in result.missing_required_columns


def test_blocks_missing_required_values(tmp_path):
    root = tmp_path / "repo"
    source = _canonical_match(root / "input.csv")
    df = pd.read_csv(source)
    df["home_team"] = ""
    df.to_csv(source, index=False)

    builder = AnalysisInputBundleBuilder(AnalysisInputBundleConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "input_bundle", base_dir=root))
    result, _ready, _validation = builder.build()

    assert result.bundle_status == ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES
    assert "home_team" in result.missing_required_values


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"
    source = _canonical_match(root / "input.csv")

    builder = AnalysisInputBundleBuilder(AnalysisInputBundleConfig(input_path=source, output_dir=root / "not_outputs", base_dir=root))
    result, _ready, _validation = builder.build()

    assert result.bundle_status == ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH


def test_no_missing_values_are_inferred_or_invented(tmp_path):
    root = tmp_path / "repo"
    source = _canonical_match(root / "input.csv")
    df = pd.read_csv(source)
    df["home_goals"] = pd.NA
    df.to_csv(source, index=False)

    builder = AnalysisInputBundleBuilder(AnalysisInputBundleConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "input_bundle", base_dir=root))
    result, ready, _validation = builder.build()

    assert result.bundle_status == ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES
    assert ready.empty


def test_output_paths_are_under_outputs_analysis_preview_input_bundle(tmp_path):
    root, summary, _manifest = _build(tmp_path)
    allowed = (root / "outputs" / "analysis_preview" / "input_bundle").resolve()

    assert allowed in Path(summary["analysis_input_preview_path"]).resolve().parents
    assert allowed in Path(summary["bundle_manifest_path"]).resolve().parents


def test_network_prediction_and_betting_logic_are_disabled_by_design(tmp_path):
    _root, summary, manifest = _build(tmp_path)

    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert not manifest["network_calls_enabled"].astype(bool).any()
    assert not manifest["prediction_logic_enabled"].astype(bool).any()
    assert not manifest["betting_logic_enabled"].astype(bool).any()


def test_no_live_scraping_provider_calls_occur():
    text = Path(bundle_preview.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_audit_returns_analysis_input_bundle_preview_ready(tmp_path):
    root, summary, _manifest = _build(tmp_path)

    table, _markdown, rec = bundle_audit.run(manifest=summary["bundle_manifest_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == ANALYSIS_INPUT_BUNDLE_PREVIEW_READY
    assert table.iloc[0]["preview_valid"]


def test_helper_works_on_tiny_fixture_canonical_match_csv(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "analysis_preview" / "input_bundle")

    assert summary["analysis_input_bundle_status"] == ANALYSIS_INPUT_BUNDLE_PREVIEW_READY
    assert summary["rows_input"] == 1
    assert summary["rows_ready"] == 1
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert summary["recommendation"] == ANALYSIS_INPUT_BUNDLE_PREVIEW_READY


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root = tmp_path / "repo"
    source = _canonical_match(root / "outputs" / "importer_preview" / "normalized" / "canonical_match_preview.csv")
    files = [
        root / "data" / "processed" / "target_clean.csv",
        root / "data" / "trusted_xg_sources" / "accepted" / "accepted_xg.csv",
        root / "data" / "trusted_xg_sources" / "raw" / "raw_source.csv",
        root / "data" / "templates" / "manual_xg_manifest_template.csv",
    ]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sentinel\n", encoding="utf-8")
    before = {path: _sha(path) for path in files}

    bundle_preview.build_analysis_input_bundle_preview(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "input_bundle", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"
    source = _canonical_match(root / "outputs" / "importer_preview" / "normalized" / "canonical_match_preview.csv")

    bundle_preview.build_analysis_input_bundle_preview(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "input_bundle", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
