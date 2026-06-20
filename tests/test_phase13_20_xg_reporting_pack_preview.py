from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_xg_reporting_pack_preview as pack_audit  # noqa: E402
import build_understat_bundesliga_2024_xg_reporting_pack_preview as helper  # noqa: E402
import build_xg_reporting_pack_preview as pack  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(tmp_path: Path, *, missing_xg: bool = False, manifest_id: str = "tiny_manifest_xg") -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    xg = root / "data" / "trusted_xg_sources" / "accepted" / "tiny_manual_xg.csv"
    target = root / "data" / "processed" / "target_clean.csv"
    manifest = root / "data" / "templates" / "manual_xg_manifest_template.csv"
    xg.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "home_xg": 1.0, "away_xg": 0.2},
        {"date": "2024-01-08", "home_team": "Gamma", "away_team": "Alpha", "home_xg": 1.5, "away_xg": "" if missing_xg else 0.7},
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


def test_builds_reporting_pack_from_accepted_manifest_entry(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = pack.build_xg_reporting_pack_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    assert summary["reporting_pack_status"] == pack.XG_REPORTING_PACK_PREVIEW_READY
    assert summary["reports_built"] == 4
    assert summary["reports_ready"] == 4


def test_pack_index_includes_all_expected_report_types(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)
    index = pd.read_csv(summary["reporting_pack_index_path"], low_memory=False)

    assert set(index["report_type"]) == set(pack.EXPECTED_REPORTS)


def test_markdown_summary_is_created(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    text = Path(summary["reporting_pack_summary_path"]).read_text(encoding="utf-8")
    assert "xG is not active in model logic" in text
    assert "Tiny League" in text


def test_all_output_paths_are_under_outputs_xg_reporting_preview(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)
    index = pd.read_csv(summary["reporting_pack_index_path"], low_memory=False)
    allowed = (root / "outputs" / "xg_reporting_preview").resolve()

    for output_path in index["output_path"]:
        resolved = Path(output_path).resolve()
        assert allowed in resolved.parents


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    before = {path: _sha(path) for path in [xg, target, manifest]}

    pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in [xg, target, manifest]} == before


def test_reports_are_ready_when_individual_builders_are_ready(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)
    index = pd.read_csv(summary["reporting_pack_index_path"], low_memory=False)

    assert index.set_index("report_type").loc["match_level_reporting_preview", "status"] == "XG_REPORTING_PREVIEW_READY"
    assert index.set_index("report_type").loc["team_xg_reporting_aggregates", "status"] == "TEAM_XG_REPORTING_AGGREGATES_READY"
    assert index.set_index("report_type").loc["rolling_xg_form_reporting", "status"] == "ROLLING_XG_FORM_REPORTING_READY"
    assert index.set_index("report_type").loc["xg_matchup_reporting_preview", "status"] == "XG_MATCHUP_REPORTING_PREVIEW_READY"


def test_blocks_unsafe_output_path(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    summary = pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "not_outputs", base_dir=root)

    assert summary["reporting_pack_status"] == pack.XG_REPORTING_PACK_PREVIEW_BLOCKED_UNSAFE_PATH


def test_blocks_failed_child_report_status(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, missing_xg=True)

    summary = pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    assert summary["reporting_pack_status"] == pack.XG_REPORTING_PACK_PREVIEW_BLOCKED_REPORT_FAILED
    assert summary["reports_ready"] < 4


def test_audit_pack_preview_ready(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    summary = pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    table, _markdown, rec = pack_audit.run(index=summary["reporting_pack_index_path"], output_dir=tmp_path / "diag", base_dir=root)

    assert rec == pack_audit.XG_REPORTING_PACK_PREVIEW_READY
    assert table.iloc[0]["reports_ready"] == 4


def test_audit_flags_forbidden_output_path(tmp_path):
    root, _xg, _target, _manifest = _fixture_root(tmp_path)
    index = root / "outputs" / "xg_reporting_preview" / "xg_reporting_pack_index.csv"
    index.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "manifest_id": "tiny_manifest_xg",
        "report_type": "match_level_reporting_preview",
        "status": "XG_REPORTING_PREVIEW_READY",
        "rows": 3,
        "output_path": str(root / "data" / "processed" / "target_clean.csv"),
        "recommendation": "XG_REPORTING_PREVIEW_READY",
    }]).to_csv(index, index=False)

    table, _markdown, rec = pack_audit.run(index=index, output_dir=tmp_path / "diag", base_dir=root)

    assert rec == pack_audit.FIX_XG_REPORTING_PACK_PREVIEW
    assert "FORBIDDEN_PRODUCTION_OUTPUT_PATH" in table.iloc[0]["blocking_reasons"]


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    before = pd.read_csv(xg, low_memory=False)

    pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    after = pd.read_csv(xg, low_memory=False)
    assert before.equals(after)


def test_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(manifest, root / "outputs" / "xg_reporting_preview", window=2)

    assert summary["reporting_pack_status"] == pack.XG_REPORTING_PACK_PREVIEW_READY
    assert summary["reports_built"] == 4
    assert summary["reports_ready"] == 4
    assert summary["recommendation"] == pack_audit.XG_REPORTING_PACK_PREVIEW_READY


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    pack.build_xg_reporting_pack_preview(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
