from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_xg_reporting_layer_closure as closure  # noqa: E402
import build_understat_bundesliga_2024_xg_reporting_layer_closure as helper  # noqa: E402
import build_xg_reporting_pack_preview as pack  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(tmp_path: Path, *, manifest_id: str = "tiny_manifest_xg") -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    xg = root / "data" / "trusted_xg_sources" / "accepted" / "tiny_manual_xg.csv"
    target = root / "data" / "processed" / "target_clean.csv"
    manifest = root / "data" / "templates" / "manual_xg_manifest_template.csv"
    xg.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "home_xg": 1.0, "away_xg": 0.2},
        {"date": "2024-01-08", "home_team": "Gamma", "away_team": "Alpha", "home_xg": 1.5, "away_xg": 0.7},
        {"date": "2024-01-15", "home_team": "Alpha", "away_team": "Gamma", "home_xg": 2.4, "away_xg": 0.4},
    ]).to_csv(xg, index=False)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "score": "1-0", "home_goals": 1, "away_goals": 0},
        {"date": "2024-01-08", "home_team": "Gamma", "away_team": "Alpha", "score": "2-2", "home_goals": 2, "away_goals": 2},
        {"date": "2024-01-15", "home_team": "Alpha", "away_team": "Gamma", "score": "0-1", "home_goals": 0, "away_goals": 1},
    ]).to_csv(target, index=False)
    pd.DataFrame([{
        "manifest_id": manifest_id,
        "xg_file_path": "data/trusted_xg_sources/accepted/tiny_manual_xg.csv",
        "target_file_path": "data/processed/target_clean.csv",
        "league": "Tiny League",
        "season": "2024",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": 3,
        "min_join_coverage_pct": 100.0,
        "notes": "tiny accepted xG",
    }]).to_csv(manifest, index=False)
    return root, xg, target, manifest


def test_closure_audit_detects_all_reporting_layers_ready(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    table, _markdown, rec = closure.run(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        preview_dir=root / "outputs" / "xg_reporting_preview",
        output_dir=root / "outputs" / "diagnostics",
        base_dir=root,
    )

    summary = closure.summarize_closure(table, rec)
    assert summary["closure_status"] == closure.XG_REPORTING_LAYER_COMPLETE
    assert rec == closure.XG_REPORTING_LAYER_COMPLETE_READY_FOR_HUMAN_DIAGNOSTICS
    assert not table["blocking"].any()


def test_closure_audit_blocks_when_reporting_pack_missing(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    table, _markdown, rec = closure.run(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        preview_dir=root / "outputs" / "xg_reporting_preview",
        output_dir=root / "outputs" / "diagnostics",
        base_dir=root,
        no_build=True,
    )

    summary = closure.summarize_closure(table, rec)
    assert summary["closure_status"] != closure.XG_REPORTING_LAYER_COMPLETE
    assert rec in {closure.BUILD_XG_REPORTING_PACK_PREVIEW, closure.FIX_XG_REPORTING_LAYER}


def test_closure_audit_blocks_when_reporting_pack_failed(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = root / "outputs" / "xg_reporting_preview"
    preview.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "manifest_id": "tiny_manifest_xg",
        "report_type": "match_level_reporting_preview",
        "status": "FAILED",
        "rows": 0,
        "output_path": str(preview / "bad.csv"),
        "recommendation": "FAILED",
    }]).to_csv(preview / "xg_reporting_pack_index.csv", index=False)

    table, _markdown, rec = closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=preview, output_dir=root / "outputs" / "diagnostics", base_dir=root, no_build=True)

    assert table[table["check_name"].eq("reporting_pack")].iloc[0]["blocking"]
    assert rec == closure.FIX_XG_REPORTING_LAYER


def test_closure_audit_records_model_integration_not_active(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    table, _markdown, _rec = closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert set(table["model_integration_status"]) == {closure.XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN}


def test_legacy_add_manual_xg_values_is_non_blocking(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    table, markdown, _rec = closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)
    row = table[table["check_name"].eq("legacy_add_manual_xg_values_non_blocking")].iloc[0]

    assert not bool(row["blocking"])
    assert "ADD_MANUAL_XG_VALUES" in markdown


def test_closure_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(manifest, root / "outputs" / "xg_reporting_preview", root / "outputs" / "diagnostics", window=2)

    assert summary["closure_status"] == closure.XG_REPORTING_LAYER_COMPLETE
    assert summary["reporting_pack_status"] == pack.XG_REPORTING_PACK_PREVIEW_READY
    assert summary["reports_ready"] == 4
    assert summary["recommendation"] == closure.XG_REPORTING_LAYER_COMPLETE_READY_FOR_HUMAN_DIAGNOSTICS


def test_closure_summary_csv_and_markdown_are_written(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert (root / "outputs" / "diagnostics" / closure.OUTPUT_CSV).exists()
    assert (root / "outputs" / "diagnostics" / closure.OUTPUT_MD).exists()


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    before = pd.read_csv(xg, low_memory=False)

    closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    after = pd.read_csv(xg, low_memory=False)
    assert before.equals(after)


def test_source_target_accepted_artifact_and_manifest_are_not_modified(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    before = {path: _sha(path) for path in [xg, target, manifest]}

    closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert {path: _sha(path) for path in [xg, target, manifest]} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
