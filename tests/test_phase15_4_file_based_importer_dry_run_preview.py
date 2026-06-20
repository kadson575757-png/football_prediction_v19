from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_file_based_importer_dry_run_preview as file_audit  # noqa: E402
import build_file_based_importer_dry_run_preview as file_preview  # noqa: E402
import build_file_based_importer_dry_run_preview_helper as helper  # noqa: E402
import build_importer_schema_contracts_preview as contracts_preview  # noqa: E402
from football_prediction_v19.importers.file_based_importer import (  # noqa: E402
    FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_FILE,
    FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_REQUIRED_COLUMNS,
    FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH,
    FILE_BASED_IMPORTER_DRY_RUN_READY,
    FileBasedImporterAdapter,
    FileBasedImporterConfig,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contracts(root: Path) -> Path:
    summary = contracts_preview.build_importer_schema_contracts_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    return Path(summary["contracts_output_path"])


def _match_csv(path: Path) -> Path:
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
        "extra_value": "keep out of contract preview",
    }]).to_csv(path, index=False)
    return path


def _xg_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "source_id": "file_csv",
        "provider_match_id": "m1",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "date": "2024-08-23",
        "home_xg": 1.4,
        "away_xg": 0.7,
        "xg_provider": "local_fixture",
        "xg_access_label": "dry_run_fixture",
    }]).to_csv(path, index=False)
    return path


def _build(tmp_path: Path) -> tuple[Path, dict[str, object], pd.DataFrame]:
    root = tmp_path / "repo"
    summary = file_preview.build_file_based_importer_dry_run_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["preview_output_path"], low_memory=False)
    return root, summary, table


def test_builds_file_based_importer_dry_run_preview(tmp_path):
    _root, summary, _table = _build(tmp_path)

    assert summary["file_importer_status"] == FILE_BASED_IMPORTER_DRY_RUN_READY
    assert summary["rows_input"] == 1
    assert summary["rows_normalized"] == 1
    assert Path(summary["preview_output_path"]).exists()


def test_validates_required_canonical_match_columns(tmp_path):
    root = tmp_path / "repo"
    contracts = _contracts(root)
    source = _match_csv(root / "fixtures" / "match.csv")

    adapter = FileBasedImporterAdapter(FileBasedImporterConfig(input_path=source, contracts_path=contracts, output_dir=root / "outputs" / "importer_preview", base_dir=root))
    result, normalized = adapter.run_dry_run()

    assert result.dry_run_status == FILE_BASED_IMPORTER_DRY_RUN_READY
    assert set(["source_id", "provider_match_id", "league", "season", "date", "home_team", "away_team", "match_status"]).issubset(normalized.columns)


def test_validates_canonical_xg_source_columns(tmp_path):
    root = tmp_path / "repo"
    contracts = _contracts(root)
    source = _xg_csv(root / "fixtures" / "xg.csv")

    adapter = FileBasedImporterAdapter(FileBasedImporterConfig(contract_id="canonical_xg_source", input_path=source, contracts_path=contracts, output_dir=root / "outputs" / "importer_preview", base_dir=root))
    result, normalized = adapter.run_dry_run()

    assert result.dry_run_status == FILE_BASED_IMPORTER_DRY_RUN_READY
    assert set(["home_xg", "away_xg", "xg_provider", "xg_access_label"]).issubset(normalized.columns)


def test_blocks_missing_input_file(tmp_path):
    root = tmp_path / "repo"
    contracts = _contracts(root)

    adapter = FileBasedImporterAdapter(FileBasedImporterConfig(input_path=root / "missing.csv", contracts_path=contracts, output_dir=root / "outputs" / "importer_preview", base_dir=root))
    result, _normalized = adapter.run_dry_run()

    assert result.dry_run_status == FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_FILE


def test_blocks_missing_required_columns(tmp_path):
    root = tmp_path / "repo"
    contracts = _contracts(root)
    source = root / "fixtures" / "bad.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"source_id": "file_csv", "date": "2024-08-23"}]).to_csv(source, index=False)

    adapter = FileBasedImporterAdapter(FileBasedImporterConfig(input_path=source, contracts_path=contracts, output_dir=root / "outputs" / "importer_preview", base_dir=root))
    result, _normalized = adapter.run_dry_run()

    assert result.dry_run_status == FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_REQUIRED_COLUMNS
    assert "provider_match_id" in result.missing_required_columns


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"
    contracts = _contracts(root)
    source = _match_csv(root / "fixtures" / "match.csv")

    adapter = FileBasedImporterAdapter(FileBasedImporterConfig(input_path=source, contracts_path=contracts, output_dir=root / "not_outputs", base_dir=root))
    result, _normalized = adapter.run_dry_run()

    assert result.dry_run_status == FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH


def test_no_missing_values_are_inferred_or_invented(tmp_path):
    root = tmp_path / "repo"
    contracts = _contracts(root)
    source = _match_csv(root / "fixtures" / "match.csv")
    df = pd.read_csv(source)
    df["home_goals"] = pd.NA
    df.to_csv(source, index=False)

    adapter = FileBasedImporterAdapter(FileBasedImporterConfig(input_path=source, contracts_path=contracts, output_dir=root / "outputs" / "importer_preview", base_dir=root))
    result, normalized = adapter.run_dry_run()

    assert result.dry_run_status == FILE_BASED_IMPORTER_DRY_RUN_READY
    assert normalized["home_goals"].isna().all()


def test_normalized_output_path_is_under_outputs_importer_preview(tmp_path):
    root, summary, _table = _build(tmp_path)
    allowed = (root / "outputs" / "importer_preview").resolve()

    assert allowed in Path(summary["normalized_output_path"]).resolve().parents


def test_network_calls_are_disabled_by_design(tmp_path):
    _root, summary, table = _build(tmp_path)

    assert summary["network_calls_enabled"] is False
    assert not table["network_calls_enabled"].astype(bool).any()


def test_no_live_scraping_provider_calls_occur():
    text = Path(file_preview.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]

    assert not any(token in text for token in forbidden)


def test_audit_returns_file_based_importer_dry_run_ready(tmp_path):
    root, summary, _table = _build(tmp_path)

    table, _markdown, rec = file_audit.run(preview=summary["preview_output_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == FILE_BASED_IMPORTER_DRY_RUN_READY
    assert table.iloc[0]["preview_valid"]


def test_helper_works_on_tiny_fixture_csv(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "importer_preview")

    assert summary["file_importer_status"] == FILE_BASED_IMPORTER_DRY_RUN_READY
    assert summary["rows_input"] == 1
    assert summary["rows_normalized"] == 1
    assert summary["network_calls_enabled"] is False
    assert summary["recommendation"] == FILE_BASED_IMPORTER_DRY_RUN_READY


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

    file_preview.build_file_based_importer_dry_run_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"

    file_preview.build_file_based_importer_dry_run_preview(output_dir=root / "outputs" / "importer_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text

