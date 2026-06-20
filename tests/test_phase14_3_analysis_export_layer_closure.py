from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_analysis_export_layer_closure as export_closure  # noqa: E402
import build_analysis_export_bundle_preview as bundle_builder  # noqa: E402
import build_understat_bundesliga_2024_analysis_export_layer_closure as helper  # noqa: E402


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


def test_closure_audit_detects_export_bundle_excel_and_xg_closure_ready(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    table, _markdown, rec = export_closure.run(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        preview_dir=root / "outputs" / "analysis_export_preview",
        xg_preview_dir=root / "outputs" / "xg_reporting_preview",
        output_dir=root / "outputs" / "diagnostics",
        base_dir=root,
    )

    summary = export_closure.summarize_export_layer(table, rec)
    assert summary["export_layer_status"] == export_closure.ANALYSIS_EXPORT_LAYER_COMPLETE
    assert summary["export_bundle_status"] == "ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY"
    assert summary["excel_workbook_status"] == "ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY"
    assert summary["xg_reporting_layer_status"] == "XG_REPORTING_LAYER_COMPLETE"
    assert rec == export_closure.ANALYSIS_EXPORT_LAYER_COMPLETE_READY_FOR_HUMAN_ANALYSIS


def test_closure_audit_blocks_when_excel_workbook_missing(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    bundle_builder.build_analysis_export_bundle_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "analysis_export_preview",
        write_preview=True,
        base_dir=root,
    )

    table, _markdown, rec = export_closure.run(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        preview_dir=root / "outputs" / "analysis_export_preview",
        xg_preview_dir=root / "outputs" / "xg_reporting_preview",
        output_dir=root / "outputs" / "diagnostics",
        base_dir=root,
        no_build=True,
    )

    excel = table[table["check_name"].eq("excel_workbook")].iloc[0]
    assert excel["blocking"]
    assert rec in {export_closure.BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW, export_closure.FIX_ANALYSIS_EXPORT_LAYER}


def test_closure_audit_blocks_when_export_bundle_missing(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    table, _markdown, rec = export_closure.run(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        preview_dir=root / "outputs" / "analysis_export_preview",
        xg_preview_dir=root / "outputs" / "xg_reporting_preview",
        output_dir=root / "outputs" / "diagnostics",
        base_dir=root,
        no_build=True,
    )

    bundle = table[table["check_name"].eq("analysis_export_bundle")].iloc[0]
    assert bundle["blocking"]
    assert rec in {export_closure.BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW, export_closure.BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW, export_closure.FIX_ANALYSIS_EXPORT_LAYER}


def test_closure_audit_blocks_when_export_bundle_failed(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    bundle_dir = root / "outputs" / "analysis_export_preview" / "tiny_manifest_xg"
    bundle_dir.mkdir(parents=True)
    pd.DataFrame([{
        "manifest_id": "tiny_manifest_xg",
        "export_name": "match_level_xg_reporting_preview.csv",
        "source_report_type": "match_level_reporting_preview",
        "source_status": "FAILED",
        "rows": 0,
        "output_path": str(bundle_dir / "missing.csv"),
        "export_status": "EXPORT_BLOCKED",
        "recommendation": "FIX_ANALYSIS_EXPORT",
    }]).to_csv(bundle_dir / "analysis_export_bundle_index.csv", index=False)

    table, _markdown, rec = export_closure.run(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        preview_dir=root / "outputs" / "analysis_export_preview",
        xg_preview_dir=root / "outputs" / "xg_reporting_preview",
        output_dir=root / "outputs" / "diagnostics",
        base_dir=root,
        no_build=True,
    )

    bundle = table[table["check_name"].eq("analysis_export_bundle")].iloc[0]
    assert bundle["blocking"]
    assert rec != export_closure.ANALYSIS_EXPORT_LAYER_COMPLETE_READY_FOR_HUMAN_ANALYSIS


def test_closure_audit_records_model_integration_not_active(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    table, _markdown, _rec = export_closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "analysis_export_preview", xg_preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert set(table["model_integration_status"]) == {export_closure.XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN}


def test_closure_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(
        manifest,
        root / "outputs" / "analysis_export_preview",
        root / "outputs" / "xg_reporting_preview",
        root / "outputs" / "diagnostics",
        window=2,
    )

    assert summary["export_layer_status"] == export_closure.ANALYSIS_EXPORT_LAYER_COMPLETE
    assert summary["export_bundle_status"] == "ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY"
    assert summary["excel_workbook_status"] == "ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY"
    assert summary["xg_reporting_layer_status"] == "XG_REPORTING_LAYER_COMPLETE"


def test_closure_summary_csv_and_markdown_are_written(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    export_closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "analysis_export_preview", xg_preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert (root / "outputs" / "diagnostics" / export_closure.OUTPUT_CSV).exists()
    assert (root / "outputs" / "diagnostics" / export_closure.OUTPUT_MD).exists()


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    before = pd.read_csv(xg, low_memory=False)

    export_closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "analysis_export_preview", xg_preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    after = pd.read_csv(xg, low_memory=False)
    assert before.equals(after)


def test_source_target_accepted_artifact_and_manifest_are_not_modified(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    before = {path: _sha(path) for path in [xg, target, manifest]}

    export_closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "analysis_export_preview", xg_preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert {path: _sha(path) for path in [xg, target, manifest]} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    export_closure.run(manifest=manifest, manifest_id="tiny_manifest_xg", preview_dir=root / "outputs" / "analysis_export_preview", xg_preview_dir=root / "outputs" / "xg_reporting_preview", output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
