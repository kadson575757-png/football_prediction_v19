from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_importer_adapter_interface_preview as adapter_audit  # noqa: E402
import build_importer_adapter_interface_preview as adapter_preview  # noqa: E402
import build_importer_adapter_interface_preview_helper as helper  # noqa: E402
from football_prediction_v19.importers.adapter_interface import (  # noqa: E402
    BaseImporterAdapter,
    ImporterAdapterConfig,
    ImporterRunContext,
    IMPORTER_ADAPTER_CONFIG_INVALID,
    IMPORTER_ADAPTER_CONTRACT_VALIDATION_FAILED,
    IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CountingPreviewAdapter(BaseImporterAdapter):
    def __init__(self, config: ImporterAdapterConfig) -> None:
        super().__init__(config)
        self.fetch_called = False
        self.normalize_called = False

    def fetch_raw(self, context: ImporterRunContext):
        self.fetch_called = True
        raise AssertionError("fetch_raw should not be called during preview")

    def normalize(self, raw, context: ImporterRunContext):
        self.normalize_called = True
        raise AssertionError("normalize should not be called during preview")


def _build(tmp_path: Path) -> tuple[Path, dict[str, object], pd.DataFrame]:
    root = tmp_path / "repo"
    summary = adapter_preview.build_importer_adapter_interface_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["adapter_output_path"], low_memory=False)
    return root, summary, table


def test_base_importer_adapter_run_preview_works_without_network():
    adapter = CountingPreviewAdapter(ImporterAdapterConfig("fbref", "FBref", ("canonical_match",), network_enabled=False))

    result = adapter.run_preview(ImporterRunContext(requested_contracts=("canonical_match",)))

    assert result.adapter_status == IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY
    assert result.network_calls_enabled is False
    assert result.rows_normalized == 0
    assert adapter.fetch_called is False
    assert adapter.normalize_called is False


def test_adapter_config_validation_works():
    adapter = CountingPreviewAdapter(ImporterAdapterConfig("", "FBref", ("canonical_match",), network_enabled=False))

    result = adapter.run_preview()

    assert result.adapter_status == IMPORTER_ADAPTER_CONFIG_INVALID


def test_contract_support_validation_works():
    adapter = CountingPreviewAdapter(ImporterAdapterConfig("fbref", "FBref", ("canonical_match",), network_enabled=False))

    result = adapter.run_preview(ImporterRunContext(requested_contracts=("canonical_xg_source",)))

    assert result.adapter_status == IMPORTER_ADAPTER_CONTRACT_VALIDATION_FAILED


def test_fetch_raw_is_not_called_during_preview():
    adapter = CountingPreviewAdapter(ImporterAdapterConfig("understat", "Understat", ("canonical_xg_source",), network_enabled=False))

    adapter.run_preview()

    assert adapter.fetch_called is False


def test_normalize_is_not_called_during_preview():
    adapter = CountingPreviewAdapter(ImporterAdapterConfig("understat", "Understat", ("canonical_xg_source",), network_enabled=False))

    adapter.run_preview()

    assert adapter.normalize_called is False


def test_builds_importer_adapter_interface_preview(tmp_path):
    _root, summary, _table = _build(tmp_path)

    assert summary["importer_adapter_interface_status"] == adapter_preview.IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY
    assert summary["adapters_registered"] == 6
    assert Path(summary["adapter_output_path"]).exists()


def test_includes_expected_source_ids(tmp_path):
    _root, _summary, table = _build(tmp_path)

    assert set(adapter_audit.EXPECTED_SOURCE_IDS).issubset(set(table["source_id"]))


def test_required_columns_exist(tmp_path):
    _root, _summary, table = _build(tmp_path)

    assert adapter_audit.REQUIRED_COLUMNS.issubset(set(table.columns))


def test_network_calls_are_disabled_by_design(tmp_path):
    _root, summary, table = _build(tmp_path)

    assert summary["network_calls_enabled"] is False
    assert not table["network_calls_enabled"].astype(bool).any()


def test_rows_normalized_remains_zero(tmp_path):
    _root, _summary, table = _build(tmp_path)

    assert (table["rows_normalized"] == 0).all()


def test_no_live_scraping_provider_calls_occur():
    text = Path(adapter_preview.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_output_paths_are_under_outputs_importer_preview(tmp_path):
    root, summary, _table = _build(tmp_path)
    allowed = (root / "outputs" / "importer_preview").resolve()

    assert allowed in Path(summary["adapter_output_path"]).resolve().parents
    assert allowed in Path(summary["adapter_summary_path"]).resolve().parents


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"

    summary = adapter_preview.build_importer_adapter_interface_preview(output_dir=root / "not_outputs", base_dir=root)

    assert summary["importer_adapter_interface_status"] == adapter_preview.IMPORTER_ADAPTER_INTERFACE_PREVIEW_BLOCKED_UNSAFE_PATH


def test_audit_returns_ready(tmp_path):
    root, summary, _table = _build(tmp_path)

    table, _markdown, rec = adapter_audit.run(preview=summary["adapter_output_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == adapter_audit.IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY
    assert table.iloc[0]["preview_valid"]


def test_helper_works_on_tiny_fixture_registry_contracts(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "importer_preview")

    assert summary["importer_adapter_interface_status"] == adapter_preview.IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY
    assert summary["adapters_registered"] == 6
    assert summary["network_calls_enabled"] is False
    assert summary["recommendation"] == adapter_audit.IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY


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

    adapter_preview.build_importer_adapter_interface_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"

    adapter_preview.build_importer_adapter_interface_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
