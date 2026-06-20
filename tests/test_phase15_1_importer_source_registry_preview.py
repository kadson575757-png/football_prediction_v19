from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_importer_source_registry_preview as registry_audit  # noqa: E402
import build_importer_source_registry_preview as registry  # noqa: E402
import build_importer_source_registry_preview_helper as helper  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_builds_importer_source_registry_preview(tmp_path):
    root = tmp_path / "repo"
    summary = registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert summary["importer_registry_status"] == registry.IMPORTER_SOURCE_REGISTRY_PREVIEW_READY
    assert summary["sources_registered"] == 6
    assert Path(summary["registry_output_path"]).exists()


def test_includes_expected_source_ids(tmp_path):
    root = tmp_path / "repo"
    summary = registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["registry_output_path"], low_memory=False)

    assert set(registry_audit.EXPECTED_SOURCE_IDS).issubset(set(table["source_id"]))


def test_registry_columns_exist(tmp_path):
    root = tmp_path / "repo"
    summary = registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["registry_output_path"], low_memory=False)

    assert set(registry.REGISTRY_COLUMNS).issubset(set(table.columns))


def test_network_calls_are_disabled_by_design(tmp_path):
    root = tmp_path / "repo"
    summary = registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["registry_output_path"], low_memory=False)

    assert summary["network_calls_enabled"] is False
    assert not table["network_calls_enabled"].astype(bool).any()
    assert set(table["implementation_status"]) == {registry.IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN}


def test_no_live_scraping_provider_calls_occur():
    text = Path(registry.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_output_paths_are_under_outputs_importer_preview(tmp_path):
    root = tmp_path / "repo"
    summary = registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    allowed = (root / "outputs" / "importer_preview").resolve()

    assert allowed in Path(summary["registry_output_path"]).resolve().parents
    assert allowed in Path(summary["registry_summary_path"]).resolve().parents


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"
    summary = registry.build_importer_source_registry_preview(output_dir=root / "not_outputs", base_dir=root)

    assert summary["importer_registry_status"] == registry.IMPORTER_SOURCE_REGISTRY_PREVIEW_BLOCKED_UNSAFE_PATH


def test_audit_returns_ready(tmp_path):
    root = tmp_path / "repo"
    summary = registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    table, _markdown, rec = registry_audit.run(registry=summary["registry_output_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == registry_audit.IMPORTER_SOURCE_REGISTRY_PREVIEW_READY
    assert table.iloc[0]["registry_valid"]


def test_helper_works_on_tiny_fixture_config(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "importer_preview")

    assert summary["importer_registry_status"] == registry.IMPORTER_SOURCE_REGISTRY_PREVIEW_READY
    assert summary["sources_registered"] == 6
    assert summary["network_calls_enabled"] is False
    assert summary["recommendation"] == registry_audit.IMPORTER_SOURCE_REGISTRY_PREVIEW_READY


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

    registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"

    registry.build_importer_source_registry_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
