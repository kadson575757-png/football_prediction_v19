from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_single_match_context_enrichment_preview as context_audit  # noqa: E402
import build_single_match_context_enrichment_preview as context_preview  # noqa: E402
import build_single_match_context_enrichment_preview_helper as helper  # noqa: E402
from football_prediction_v19.analysis.single_match_context_enrichment import (  # noqa: E402
    CONTEXT_OPTIONAL_MISSING,
    SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_BASE_REPORT,
    SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_REQUIRED_COLUMNS,
    SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_UNSAFE_PATH,
    SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY,
    SingleMatchContextEnrichmentBuilder,
    SingleMatchContextEnrichmentConfig,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_manifest(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "report_id": "single_match_analysis_report_preview",
        "source_id": "file_csv",
        "provider_match_id": "m1",
        "league": "Preview League",
        "season": "2024",
        "input_path": "input.csv",
        "report_path": "report.md",
        "summary_path": "summary.csv",
        "rows_input": 1,
        "rows_reported": 1,
        "missing_required_columns": "",
        "missing_required_values": "",
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "report_status": "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY",
        "recommendation": "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY",
        "notes": "preview",
    }]).to_csv(path, index=False)
    return path


def _build(tmp_path: Path):
    root = tmp_path / "repo"
    manifest = _base_manifest(root / "outputs" / "analysis_preview" / "single_match_report" / "single_match_analysis_report_manifest.csv")
    summary = context_preview.build_single_match_context_enrichment_preview(base_report_manifest=manifest, output_dir=root / "outputs" / "analysis_preview" / "single_match_context", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["manifest_path"], low_memory=False)
    return root, summary, table


def test_builds_single_match_context_enrichment_preview(tmp_path):
    _root, summary, _table = _build(tmp_path)

    assert summary["single_match_context_enrichment_status"] == SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY
    assert summary["rows_reported"] == 1
    assert summary["contexts_checked"] > 0


def test_builds_missing_single_match_report_when_default_base_report_missing(tmp_path):
    root = tmp_path / "repo"

    summary = context_preview.build_single_match_context_enrichment_preview(output_dir=root / "outputs" / "analysis_preview" / "single_match_context", write_preview=True, base_dir=root)

    assert summary["single_match_context_enrichment_status"] == SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY
    assert (root / "outputs" / "analysis_preview" / "single_match_report" / "single_match_analysis_report_manifest.csv").exists()


def test_validates_required_base_report_manifest_columns(tmp_path):
    root = tmp_path / "repo"
    manifest = _base_manifest(root / "base.csv")

    builder = SingleMatchContextEnrichmentBuilder(SingleMatchContextEnrichmentConfig(base_report_manifest_path=manifest, output_dir=root / "outputs" / "analysis_preview" / "single_match_context", base_dir=root))
    result, summary, _markdown = builder.build()

    assert result.enrichment_status == SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY
    assert set(["context_name", "context_status", "input_path", "rows_available", "rows_matched", "warning", "recommendation"]).issubset(summary.columns)


def test_blocks_missing_base_report_when_build_missing_disabled(tmp_path):
    root = tmp_path / "repo"

    summary = context_preview.build_single_match_context_enrichment_preview(output_dir=root / "outputs" / "analysis_preview" / "single_match_context", write_preview=True, build_missing_base_report=False, base_dir=root)

    assert summary["single_match_context_enrichment_status"] == SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_BASE_REPORT


def test_blocks_missing_required_manifest_columns(tmp_path):
    root = tmp_path / "repo"
    manifest = root / "bad.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"source_id": "file_csv"}]).to_csv(manifest, index=False)

    builder = SingleMatchContextEnrichmentBuilder(SingleMatchContextEnrichmentConfig(base_report_manifest_path=manifest, output_dir=root / "outputs" / "analysis_preview" / "single_match_context", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.enrichment_status == SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_REQUIRED_COLUMNS


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"
    manifest = _base_manifest(root / "base.csv")

    builder = SingleMatchContextEnrichmentBuilder(SingleMatchContextEnrichmentConfig(base_report_manifest_path=manifest, output_dir=root / "not_outputs", base_dir=root))
    result, _summary, _markdown = builder.build()

    assert result.enrichment_status == SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_UNSAFE_PATH


def test_optional_context_missing_does_not_fail_and_is_warning(tmp_path):
    _root, summary, _table = _build(tmp_path)
    context_summary = pd.read_csv(summary["summary_path"], low_memory=False)

    assert summary["single_match_context_enrichment_status"] == SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY
    assert CONTEXT_OPTIONAL_MISSING in set(context_summary["context_status"])
    assert summary["contexts_missing_optional"] > 0


def test_no_missing_context_values_are_inferred_or_invented(tmp_path):
    _root, summary, _table = _build(tmp_path)
    context_summary = pd.read_csv(summary["summary_path"], low_memory=False)

    missing = context_summary[context_summary["context_status"].eq(CONTEXT_OPTIONAL_MISSING)]
    assert (missing["rows_available"] == 0).all()
    assert (missing["rows_matched"] == 0).all()


def test_output_paths_are_under_outputs_analysis_preview_single_match_context(tmp_path):
    root, summary, _table = _build(tmp_path)
    allowed = (root / "outputs" / "analysis_preview" / "single_match_context").resolve()

    assert allowed in Path(summary["report_path"]).resolve().parents
    assert allowed in Path(summary["summary_path"]).resolve().parents
    assert allowed in Path(summary["manifest_path"]).resolve().parents


def test_markdown_report_contains_required_preview_safety_context_sections(tmp_path):
    _root, summary, _table = _build(tmp_path)
    text = Path(summary["report_path"]).read_text(encoding="utf-8")

    for section in [
        "Context Enrichment Preview Header",
        "Match Identity",
        "Base Single-Match Report Status",
        "Analysis Input Bundle Status",
        "Importer / Canonical Match Context",
        "xG Reporting Pack Context",
        "Team xG Aggregate Context",
        "Rolling xG Form Context",
        "xG Matchup Context",
        "Missing Optional Context Warnings",
        "Prediction Logic Status",
        "Betting Logic Status",
        "Network / Scraping Status",
        "Safety Notes",
        "Recommendation",
        "preview-only context enrichment",
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
    text = Path(context_preview.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_audit_returns_single_match_context_enrichment_preview_ready(tmp_path):
    root, summary, _table = _build(tmp_path)

    table, _markdown, rec = context_audit.run(manifest=summary["manifest_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY
    assert table.iloc[0]["preview_valid"]


def test_helper_works_on_tiny_fixture_base_report_manifest(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "analysis_preview" / "single_match_context")

    assert summary["single_match_context_enrichment_status"] == SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY
    assert summary["rows_reported"] == 1
    assert summary["contexts_checked"] > 0
    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root = tmp_path / "repo"
    manifest = _base_manifest(root / "base.csv")
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

    context_preview.build_single_match_context_enrichment_preview(base_report_manifest=manifest, output_dir=root / "outputs" / "analysis_preview" / "single_match_context", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"
    manifest = _base_manifest(root / "base.csv")

    context_preview.build_single_match_context_enrichment_preview(base_report_manifest=manifest, output_dir=root / "outputs" / "analysis_preview" / "single_match_context", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text

