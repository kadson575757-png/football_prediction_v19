from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_importer_schema_contracts_preview as contracts_audit  # noqa: E402
import build_importer_schema_contracts_preview as contracts  # noqa: E402
import build_importer_schema_contracts_preview_helper as helper  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(tmp_path: Path) -> tuple[Path, dict[str, object], pd.DataFrame]:
    root = tmp_path / "repo"
    summary = contracts.build_importer_schema_contracts_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["contracts_output_path"], low_memory=False)
    return root, summary, table


def test_builds_importer_schema_contracts_preview(tmp_path):
    _root, summary, _table = _build(tmp_path)

    assert summary["importer_schema_contracts_status"] == contracts.IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY
    assert summary["contracts_registered"] == 7
    assert Path(summary["contracts_output_path"]).exists()


def test_includes_expected_canonical_contract_ids(tmp_path):
    _root, _summary, table = _build(tmp_path)

    assert set(contracts_audit.EXPECTED_CONTRACT_IDS).issubset(set(table["contract_id"]))


def test_required_columns_exist(tmp_path):
    _root, _summary, table = _build(tmp_path)

    assert contracts_audit.REQUIRED_COLUMNS.issubset(set(table.columns))


def test_required_canonical_match_fields_exist(tmp_path):
    _root, _summary, table = _build(tmp_path)
    fields = set(table.loc[table["contract_id"].eq("canonical_match"), "field_name"])

    assert contracts_audit.REQUIRED_MATCH_FIELDS.issubset(fields)


def test_required_canonical_xg_source_fields_exist(tmp_path):
    _root, _summary, table = _build(tmp_path)
    fields = set(table.loc[table["contract_id"].eq("canonical_xg_source"), "field_name"])

    assert contracts_audit.REQUIRED_XG_FIELDS.issubset(fields)


def test_odds_snapshot_contract_is_contract_only_and_does_not_fetch_odds(tmp_path):
    _root, _summary, table = _build(tmp_path)
    odds = table[table["contract_id"].eq("canonical_odds_snapshot")]

    assert not odds.empty
    assert set(["market_type", "bookmaker", "odds_home", "odds_draw", "odds_away", "captured_at"]).issubset(set(odds["field_name"]))
    assert set(odds["implementation_status"]) == {contracts.IMPORTER_SCHEMA_NETWORK_DISABLED_BY_DESIGN}
    assert not odds["network_calls_enabled"].astype(bool).any()


def test_network_calls_are_disabled_by_design(tmp_path):
    _root, summary, table = _build(tmp_path)

    assert summary["network_calls_enabled"] is False
    assert not table["network_calls_enabled"].astype(bool).any()


def test_no_live_scraping_provider_calls_occur():
    text = Path(contracts.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_output_paths_are_under_outputs_importer_preview(tmp_path):
    root, summary, _table = _build(tmp_path)
    allowed = (root / "outputs" / "importer_preview").resolve()

    assert allowed in Path(summary["contracts_output_path"]).resolve().parents
    assert allowed in Path(summary["contracts_summary_path"]).resolve().parents


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"
    summary = contracts.build_importer_schema_contracts_preview(output_dir=root / "not_outputs", base_dir=root)

    assert summary["importer_schema_contracts_status"] == contracts.IMPORTER_SCHEMA_CONTRACTS_PREVIEW_BLOCKED_UNSAFE_PATH


def test_audit_returns_ready(tmp_path):
    root, summary, _table = _build(tmp_path)

    table, _markdown, rec = contracts_audit.run(contracts=summary["contracts_output_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == contracts_audit.IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY
    assert table.iloc[0]["contracts_valid"]


def test_helper_works_on_tiny_fixture_registry_config(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "importer_preview")

    assert summary["importer_schema_contracts_status"] == contracts.IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY
    assert summary["contracts_registered"] == 7
    assert summary["network_calls_enabled"] is False
    assert summary["recommendation"] == contracts_audit.IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY


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

    contracts.build_importer_schema_contracts_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"

    contracts.build_importer_schema_contracts_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
