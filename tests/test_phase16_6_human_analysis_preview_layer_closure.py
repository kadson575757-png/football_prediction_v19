from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_human_analysis_preview_layer_closure as closure  # noqa: E402
import build_human_analysis_preview_layer_closure_helper as helper  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(tmp_path: Path):
    root = tmp_path / "repo"
    table, markdown, rec = closure.run(output_dir=root / "outputs" / "diagnostics", base_dir=root)
    return root, table.iloc[0].to_dict(), markdown, rec


def test_closure_audit_builds_verifies_full_human_analysis_preview_layer(tmp_path):
    _root, row, _markdown, _rec = _run(tmp_path)

    assert row["closure_status"] == closure.HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE
    assert row["pipeline_status"] == "HUMAN_MATCH_PIPELINE_PREVIEW_READY"


def test_helper_returns_human_analysis_preview_layer_complete(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    row = helper.run_workflow(root / "outputs" / "diagnostics")

    assert row["closure_status"] == closure.HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE
    assert row["recommendation"] == closure.READY_RECOMMENDATION


def test_all_prerequisite_statuses_are_present_and_ready(tmp_path):
    _root, row, _markdown, _rec = _run(tmp_path)

    assert row["human_report_status"] == "HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY"
    assert row["context_enrichment_status"] == "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY"
    assert row["single_match_report_status"] == "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY"
    assert row["input_bundle_status"] == "ANALYSIS_INPUT_BUNDLE_PREVIEW_READY"
    assert row["file_importer_status"] == "FILE_BASED_IMPORTER_DRY_RUN_READY"
    assert row["adapter_interface_status"] == "IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY"
    assert row["schema_contract_status"] == "IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY"
    assert row["source_registry_status"] == "IMPORTER_SOURCE_REGISTRY_PREVIEW_READY"


def test_rows_steps_and_disabled_gates(tmp_path):
    _root, row, _markdown, _rec = _run(tmp_path)

    assert row["rows_reported"] == 1
    assert row["steps_failed"] == 0
    assert row["network_calls_enabled"] is False
    assert row["prediction_logic_enabled"] is False
    assert row["betting_logic_enabled"] is False
    assert row["model_integration_status"] == closure.MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN


def test_closure_markdown_contains_required_sections_and_ready_text(tmp_path):
    _root, _row, markdown, _rec = _run(tmp_path)

    for section in [
        "Phase 16.6 Closure Header",
        "Human Analysis Preview Layer Status",
        "Pipeline Status",
        "Human Report Status",
        "Context Enrichment Status",
        "Single Match Report Status",
        "Analysis Input Bundle Status",
        "File-Based Importer Status",
        "Importer Contracts Status",
        "Safety Gates",
        "Missing Optional Context Summary",
        "Model / Prediction / Betting Integration Status",
        "Closure Recommendation",
        "ready for human review workflows: yes",
        "optional missing context is summarized and not inferred",
    ]:
        assert section in markdown


def test_no_live_scraping_provider_calls_or_inference_language():
    text = Path(closure.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)
    assert "not inferred" in text


def test_output_paths_are_under_outputs_diagnostics(tmp_path):
    root, _row, _markdown, _rec = _run(tmp_path)

    assert (root / "outputs" / "diagnostics" / "human_analysis_preview_layer_closure_summary.csv").exists()
    assert (root / "outputs" / "diagnostics" / "human_analysis_preview_layer_closure_summary.md").exists()


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root = tmp_path / "repo"
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

    closure.run(output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"

    closure.run(output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text

