from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_human_match_analysis_report_preview as human_audit  # noqa: E402
import build_human_match_analysis_report_preview as human_preview  # noqa: E402
import build_human_match_analysis_report_preview_helper as helper  # noqa: E402
from football_prediction_v19.analysis.human_match_analysis_report import (  # noqa: E402
    HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_CONTEXT,
    HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS,
    HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH,
    HUMAN_MATCH_ANALYSIS_REPORT_CONTEXT_OPTIONAL_MISSING,
    HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY,
    HumanMatchAnalysisReportBuilder,
    HumanMatchAnalysisReportConfig,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _context_manifest(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "enrichment_id": "single_match_context_enrichment_preview",
        "source_id": "file_csv",
        "provider_match_id": "m1",
        "league": "Preview League",
        "season": "2024",
        "base_report_manifest_path": "base.csv",
        "output_report_path": "context.md",
        "output_summary_path": "context_summary.csv",
        "rows_reported": 1,
        "contexts_checked": 6,
        "contexts_available": 2,
        "contexts_missing_optional": 4,
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "enrichment_status": "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY",
        "recommendation": "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY",
        "notes": "preview",
    }]).to_csv(path, index=False)
    return path


def _build(tmp_path: Path):
    root = tmp_path / "repo"
    manifest = _context_manifest(root / "outputs" / "analysis_preview" / "single_match_context" / "single_match_context_enrichment_manifest.csv")
    summary = human_preview.build_human_match_analysis_report_preview(context_manifest=manifest, output_dir=root / "outputs" / "analysis_preview" / "human_match_report", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["manifest_path"], low_memory=False)
    return root, summary, table


def test_builds_human_match_analysis_report_preview(tmp_path):
    _root, summary, _table = _build(tmp_path)

    assert summary["human_match_report_status"] == HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert summary["rows_reported"] == 1
    assert summary["contexts_checked"] == 6


def test_builds_missing_context_enrichment_when_default_context_manifest_missing(tmp_path):
    root = tmp_path / "repo"

    summary = human_preview.build_human_match_analysis_report_preview(output_dir=root / "outputs" / "analysis_preview" / "human_match_report", write_preview=True, base_dir=root)

    assert summary["human_match_report_status"] == HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert (root / "outputs" / "analysis_preview" / "single_match_context" / "single_match_context_enrichment_manifest.csv").exists()


def test_validates_required_context_manifest_columns(tmp_path):
    root = tmp_path / "repo"
    manifest = _context_manifest(root / "context.csv")

    builder = HumanMatchAnalysisReportBuilder(HumanMatchAnalysisReportConfig(context_manifest_path=manifest, output_dir=root / "outputs" / "analysis_preview" / "human_match_report", base_dir=root))
    result, summary, _markdown = builder.build()

    assert result.human_report_status == HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert set(["section_name", "section_status", "rows_available", "rows_used", "warning", "recommendation", "notes"]).issubset(summary.columns)


def test_blocks_missing_context_manifest_when_build_missing_disabled(tmp_path):
    root = tmp_path / "repo"

    summary = human_preview.build_human_match_analysis_report_preview(output_dir=root / "outputs" / "analysis_preview" / "human_match_report", write_preview=True, build_missing_context=False, base_dir=root)

    assert summary["human_match_report_status"] == HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_CONTEXT


def test_blocks_missing_required_manifest_columns(tmp_path):
    root = tmp_path / "repo"
    manifest = root / "bad.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"source_id": "file_csv"}]).to_csv(manifest, index=False)

    builder = HumanMatchAnalysisReportBuilder(HumanMatchAnalysisReportConfig(context_manifest_path=manifest, output_dir=root / "outputs" / "analysis_preview" / "human_match_report", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.human_report_status == HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"
    manifest = _context_manifest(root / "context.csv")

    builder = HumanMatchAnalysisReportBuilder(HumanMatchAnalysisReportConfig(context_manifest_path=manifest, output_dir=root / "not_outputs", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.human_report_status == HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH


def test_optional_context_missing_does_not_fail_and_is_warning(tmp_path):
    _root, summary, _table = _build(tmp_path)
    report_summary = pd.read_csv(summary["summary_path"], low_memory=False)

    assert summary["human_match_report_status"] == HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert HUMAN_MATCH_ANALYSIS_REPORT_CONTEXT_OPTIONAL_MISSING in set(report_summary["section_status"])
    assert summary["contexts_missing_optional"] == 4


def test_no_missing_context_values_are_inferred_or_invented(tmp_path):
    _root, summary, _table = _build(tmp_path)
    report_summary = pd.read_csv(summary["summary_path"], low_memory=False)
    missing = report_summary[report_summary["section_status"].eq(HUMAN_MATCH_ANALYSIS_REPORT_CONTEXT_OPTIONAL_MISSING)]

    assert (missing["rows_used"] == 0).all()
    assert missing["warning"].str.contains("not inferred or invented").all()


def test_output_paths_are_under_outputs_analysis_preview_human_match_report(tmp_path):
    root, summary, _table = _build(tmp_path)
    allowed = (root / "outputs" / "analysis_preview" / "human_match_report").resolve()

    assert allowed in Path(summary["report_path"]).resolve().parents
    assert allowed in Path(summary["summary_path"]).resolve().parents
    assert allowed in Path(summary["manifest_path"]).resolve().parents


def test_markdown_report_contains_required_human_preview_safety_no_bet_sections(tmp_path):
    _root, summary, _table = _build(tmp_path)
    text = Path(summary["report_path"]).read_text(encoding="utf-8")

    for section in [
        "Human Match Analysis Preview Header",
        "Match Identity",
        "Data Quality / Source Status",
        "Available Canonical Match Data",
        "Context Availability Overview",
        "Importer / File-Based Source Context",
        "xG Reporting Context",
        "Team xG Aggregate Context",
        "Rolling xG Form Context",
        "xG Matchup Context",
        "Missing Context Warnings",
        "Prediction Logic Status",
        "Betting / Staking Logic Status",
        "No-Bet / Disabled Tips Notice",
        "Safety Notes",
        "Human Review Recommendation",
        "Next-Step Recommendation",
        "preview-only human-facing analysis report",
        "No model prediction was run",
        "No betting/staking recommendation was generated",
        "No live external data was fetched",
        "Missing optional context is not inferred or invented",
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
    text = Path(human_preview.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_audit_returns_human_match_analysis_report_preview_ready(tmp_path):
    root, summary, _table = _build(tmp_path)

    table, _markdown, rec = human_audit.run(manifest=summary["manifest_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert table.iloc[0]["preview_valid"]


def test_helper_works_on_tiny_fixture_context_manifest(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "analysis_preview" / "human_match_report")

    assert summary["human_match_report_status"] == HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    assert summary["rows_reported"] == 1
    assert summary["contexts_checked"] > 0
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root = tmp_path / "repo"
    manifest = _context_manifest(root / "context.csv")
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

    human_preview.build_human_match_analysis_report_preview(context_manifest=manifest, output_dir=root / "outputs" / "analysis_preview" / "human_match_report", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"
    manifest = _context_manifest(root / "context.csv")

    human_preview.build_human_match_analysis_report_preview(context_manifest=manifest, output_dir=root / "outputs" / "analysis_preview" / "human_match_report", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text

