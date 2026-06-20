from __future__ import annotations

import builtins
import hashlib
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_analysis_excel_workbook_preview as workbook_audit  # noqa: E402
import build_analysis_excel_workbook_preview as workbook  # noqa: E402
import build_understat_bundesliga_2024_analysis_excel_workbook_preview as helper  # noqa: E402


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


def _load_workbook(path: str | Path):
    openpyxl = pytest.importorskip("openpyxl")
    return openpyxl.load_workbook(path, read_only=True, data_only=True)


def test_builds_excel_workbook_from_analysis_export_bundle(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = workbook.build_analysis_excel_workbook_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "analysis_export_preview",
        write_preview=True,
        base_dir=root,
    )

    assert summary["excel_workbook_status"] == workbook.ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY
    assert Path(summary["workbook_path"]).exists()


def test_workbook_includes_expected_sheets(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)
    wb = _load_workbook(summary["workbook_path"])

    assert set(workbook_audit.EXPECTED_SHEETS).issubset(set(wb.sheetnames))


def test_readme_sheet_includes_manifest_and_model_integration_status(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)
    wb = _load_workbook(summary["workbook_path"])
    values = [str(cell.value) for row in wb["README"].iter_rows() for cell in row if cell.value is not None]
    joined = " | ".join(values)

    assert "tiny_manifest_xg" in joined
    assert workbook.XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN in joined


def test_bundle_index_sheet_mirrors_export_bundle_index(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)
    wb = _load_workbook(summary["workbook_path"])
    bundle_index = pd.read_csv(Path(summary["workbook_path"]).parent / "analysis_export_bundle_index.csv", low_memory=False)

    assert wb["Bundle_Index"].max_row - 1 == len(bundle_index)


def test_key_data_sheets_have_deterministic_row_counts(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)
    wb = _load_workbook(summary["workbook_path"])

    assert wb["Match_Level"].max_row - 1 == 3
    assert wb["Team_Aggregates"].max_row - 1 == 3
    assert wb["Rolling_Form"].max_row - 1 == 6
    assert wb["Matchup_Preview"].max_row - 1 == 3
    assert wb["Reporting_Pack"].max_row - 1 == 4


def test_workbook_output_path_is_under_analysis_export_preview(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)
    allowed = (root / "outputs" / "analysis_export_preview").resolve()

    assert allowed in Path(summary["workbook_path"]).resolve().parents


def test_blocks_unsafe_output_path(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "not_outputs", base_dir=root)

    assert summary["excel_workbook_status"] == workbook.ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_UNSAFE_PATH


def test_handles_missing_openpyxl_dependency_cleanly(monkeypatch, tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("openpyxl unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", base_dir=root)

    assert summary["excel_workbook_status"] == workbook.ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_MISSING_DEPENDENCY


def test_audit_excel_workbook_ready(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)

    table, _markdown, rec = workbook_audit.run(workbook=summary["workbook_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == workbook_audit.ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY
    assert table.iloc[0]["model_integration_status"] == workbook.XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    before = {path: _sha(path) for path in [xg, target, manifest]}

    workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in [xg, target, manifest]} == before


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    before = pd.read_csv(xg, low_memory=False)

    workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)

    after = pd.read_csv(xg, low_memory=False)
    assert before.equals(after)


def test_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(manifest, root / "outputs" / "analysis_export_preview", window=2)

    assert summary["excel_workbook_status"] == workbook.ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY
    assert summary["recommendation"] == workbook_audit.ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY
    assert summary["sheets_written"] >= 7


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    workbook.build_analysis_excel_workbook_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "analysis_export_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
