from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_single_match_analysis_report_preview as report_audit  # noqa: E402
import build_single_match_analysis_report_preview as report_preview  # noqa: E402
import build_single_match_analysis_report_preview_helper as helper  # noqa: E402
from football_prediction_v19.analysis.single_match_report import (  # noqa: E402
    SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MATCH_NOT_FOUND,
    SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT_BUNDLE,
    SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS,
    SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_VALUES,
    SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH,
    SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY,
    SingleMatchAnalysisReportBuilder,
    SingleMatchAnalysisReportConfig,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle(path: Path) -> Path:
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
    }]).to_csv(path, index=False)
    return path


def _build(tmp_path: Path) -> tuple[Path, dict[str, object], pd.DataFrame]:
    root = tmp_path / "repo"
    source = _bundle(root / "outputs" / "analysis_preview" / "input_bundle" / "canonical_match_analysis_input_preview.csv")
    summary = report_preview.build_single_match_analysis_report_preview(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "single_match_report", write_preview=True, base_dir=root)
    manifest = pd.read_csv(summary["manifest_path"], low_memory=False)
    return root, summary, manifest


def test_builds_single_match_analysis_report_preview(tmp_path):
    _root, summary, _manifest = _build(tmp_path)

    assert summary["single_match_report_status"] == SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert summary["rows_input"] == 1
    assert summary["rows_reported"] == 1
    assert Path(summary["report_path"]).exists()


def test_builds_missing_analysis_input_bundle_when_default_input_missing(tmp_path):
    root = tmp_path / "repo"

    summary = report_preview.build_single_match_analysis_report_preview(output_dir=root / "outputs" / "analysis_preview" / "single_match_report", write_preview=True, base_dir=root)

    assert summary["single_match_report_status"] == SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert (root / "outputs" / "analysis_preview" / "input_bundle" / "canonical_match_analysis_input_preview.csv").exists()


def test_validates_required_canonical_match_columns(tmp_path):
    root = tmp_path / "repo"
    source = _bundle(root / "input.csv")

    builder = SingleMatchAnalysisReportBuilder(SingleMatchAnalysisReportConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "single_match_report", base_dir=root))
    result, summary, _markdown = builder.build()

    assert result.report_status == SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert summary.iloc[0]["provider_match_id"] == "m1"


def test_blocks_missing_input_bundle_when_build_missing_disabled(tmp_path):
    root = tmp_path / "repo"

    summary = report_preview.build_single_match_analysis_report_preview(output_dir=root / "outputs" / "analysis_preview" / "single_match_report", write_preview=True, build_missing_input_bundle=False, base_dir=root)

    assert summary["single_match_report_status"] == SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT_BUNDLE


def test_blocks_missing_required_columns(tmp_path):
    root = tmp_path / "repo"
    source = root / "input.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"source_id": "file_csv", "date": "2024-08-23"}]).to_csv(source, index=False)

    builder = SingleMatchAnalysisReportBuilder(SingleMatchAnalysisReportConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "single_match_report", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.report_status == SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS
    assert "provider_match_id" in result.missing_required_columns


def test_blocks_missing_required_values(tmp_path):
    root = tmp_path / "repo"
    source = _bundle(root / "input.csv")
    df = pd.read_csv(source)
    df["home_team"] = ""
    df.to_csv(source, index=False)

    builder = SingleMatchAnalysisReportBuilder(SingleMatchAnalysisReportConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "single_match_report", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.report_status == SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_VALUES
    assert "home_team" in result.missing_required_values


def test_blocks_unknown_match_id(tmp_path):
    root = tmp_path / "repo"
    source = _bundle(root / "input.csv")

    builder = SingleMatchAnalysisReportBuilder(SingleMatchAnalysisReportConfig(input_path=source, match_id="missing", output_dir=root / "outputs" / "analysis_preview" / "single_match_report", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.report_status == SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MATCH_NOT_FOUND


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"
    source = _bundle(root / "input.csv")

    builder = SingleMatchAnalysisReportBuilder(SingleMatchAnalysisReportConfig(input_path=source, output_dir=root / "not_outputs", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.report_status == SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH


def test_no_missing_values_are_inferred_or_invented(tmp_path):
    root = tmp_path / "repo"
    source = _bundle(root / "input.csv")
    df = pd.read_csv(source)
    df["home_goals"] = pd.NA
    df.to_csv(source, index=False)

    builder = SingleMatchAnalysisReportBuilder(SingleMatchAnalysisReportConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "single_match_report", base_dir=root))
    result, summary, _markdown = builder.build()

    assert result.report_status == SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_VALUES
    assert summary.empty


def test_output_paths_are_under_outputs_analysis_preview_single_match_report(tmp_path):
    root, summary, _manifest = _build(tmp_path)
    allowed = (root / "outputs" / "analysis_preview" / "single_match_report").resolve()

    assert allowed in Path(summary["report_path"]).resolve().parents
    assert allowed in Path(summary["summary_path"]).resolve().parents
    assert allowed in Path(summary["manifest_path"]).resolve().parents


def test_markdown_report_contains_required_preview_safety_sections(tmp_path):
    _root, summary, _manifest = _build(tmp_path)
    text = Path(summary["report_path"]).read_text(encoding="utf-8")

    for section in [
        "Analysis Report Preview Header",
        "Match Identity",
        "Data Source / Contract",
        "Input Bundle Validation",
        "Score / Match Status",
        "Available Canonical Fields",
        "Missing Data Warnings",
        "Prediction Logic Status",
        "Betting Logic Status",
        "Network / Scraping Status",
        "Safety Notes",
        "Recommendation",
        "preview-only analysis report",
        "No model prediction was run",
        "No betting/staking recommendation was generated",
        "No live external data was fetched",
    ]:
        assert section in text


def test_network_prediction_and_betting_logic_are_disabled_by_design(tmp_path):
    _root, summary, manifest = _build(tmp_path)

    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert not manifest["network_calls_enabled"].astype(bool).any()
    assert not manifest["prediction_logic_enabled"].astype(bool).any()
    assert not manifest["betting_logic_enabled"].astype(bool).any()


def test_no_live_scraping_provider_calls_occur():
    text = Path(report_preview.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_audit_returns_single_match_analysis_report_preview_ready(tmp_path):
    root, summary, _manifest = _build(tmp_path)

    table, _markdown, rec = report_audit.run(manifest=summary["manifest_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert table.iloc[0]["preview_valid"]


def test_helper_works_on_tiny_fixture_canonical_match_csv_input_bundle(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "analysis_preview" / "single_match_report")

    assert summary["single_match_report_status"] == SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert summary["rows_input"] == 1
    assert summary["rows_reported"] == 1
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert summary["recommendation"] == SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root = tmp_path / "repo"
    source = _bundle(root / "outputs" / "analysis_preview" / "input_bundle" / "canonical_match_analysis_input_preview.csv")
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

    report_preview.build_single_match_analysis_report_preview(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "single_match_report", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"
    source = _bundle(root / "outputs" / "analysis_preview" / "input_bundle" / "canonical_match_analysis_input_preview.csv")

    report_preview.build_single_match_analysis_report_preview(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "single_match_report", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text

