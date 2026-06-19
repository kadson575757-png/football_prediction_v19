from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_xg_reporting_preview as audit_reporting  # noqa: E402
import build_understat_bundesliga_2024_xg_reporting_preview as helper  # noqa: E402
import build_xg_reporting_preview as reporting  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(
    tmp_path: Path,
    *,
    missing_xg: bool = False,
    manifest_id: str = "tiny_manifest_xg",
) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    xg = root / "data" / "trusted_xg_sources" / "accepted" / "tiny_manual_xg.csv"
    target = root / "data" / "processed" / "target_clean.csv"
    manifest = root / "data" / "templates" / "manual_xg_manifest_template.csv"
    xg.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Home 1", "away_team": "Away 1", "home_xg": 1.5, "away_xg": 0.5},
        {"date": "2024-01-02", "home_team": "Home 2", "away_team": "Away 2", "home_xg": "" if missing_xg else 0.4, "away_xg": 1.2},
    ]).to_csv(xg, index=False)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Home 1", "away_team": "Away 1", "score": "2-0", "home_goals": 2, "away_goals": 0},
        {"date": "2024-01-02", "home_team": "Home 2", "away_team": "Away 2", "score": "1-1", "home_goals": 1, "away_goals": 1},
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
        "expected_rows": 2,
        "min_join_coverage_pct": 100.0,
        "notes": "tiny accepted xG",
    }]).to_csv(manifest, index=False)
    return root, xg, target, manifest


def _build(tmp_path: Path, *, missing_xg: bool = False) -> tuple[dict[str, object], Path, Path, Path, Path]:
    root, xg, target, manifest = _fixture_root(tmp_path, missing_xg=missing_xg)
    summary = reporting.build_xg_reporting_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )
    return summary, root, xg, target, manifest


def test_builds_reporting_preview_from_accepted_manifest_entry(tmp_path):
    summary, _root, _xg, _target, _manifest = _build(tmp_path)

    assert summary["reporting_status"] == reporting.XG_REPORTING_PREVIEW_READY
    assert summary["rows_reported"] == 2
    assert Path(summary["reporting_output_path"]).exists()


def test_includes_required_reporting_columns(tmp_path):
    summary, *_ = _build(tmp_path)
    preview = pd.read_csv(summary["reporting_output_path"], low_memory=False)

    for col in reporting.REPORTING_COLUMNS:
        assert col in preview.columns


def test_preserves_row_count_and_identity_columns(tmp_path):
    summary, _root, _xg, target, _manifest = _build(tmp_path)
    preview = pd.read_csv(summary["reporting_output_path"], low_memory=False)
    target_df = pd.read_csv(target, low_memory=False)

    assert len(preview) == len(target_df)
    assert preview[["date", "home_team", "away_team", "score", "home_goals", "away_goals"]].equals(
        target_df[["date", "home_team", "away_team", "score", "home_goals", "away_goals"]]
    )


def test_computes_xg_total_and_diff_from_accepted_xg_only(tmp_path):
    summary, _root, xg, _target, _manifest = _build(tmp_path)
    preview = pd.read_csv(summary["reporting_output_path"], low_memory=False)
    artifact = pd.read_csv(xg, low_memory=False)

    assert preview.loc[0, "xg_total"] == artifact.loc[0, "home_xg"] + artifact.loc[0, "away_xg"]
    assert preview.loc[0, "xg_diff_home"] == artifact.loc[0, "home_xg"] - artifact.loc[0, "away_xg"]


def test_computes_xg_result_label_deterministically(tmp_path):
    summary, *_ = _build(tmp_path)
    preview = pd.read_csv(summary["reporting_output_path"], low_memory=False)

    assert list(preview["xg_result_label"]) == ["H", "A"]
    assert list(preview["actual_result_label"]) == ["H", "D"]
    assert list(preview["xg_result_matches_actual"]) == [True, False]


def test_does_not_infer_missing_xg_and_blocks(tmp_path):
    summary, *_ = _build(tmp_path, missing_xg=True)

    assert summary["reporting_status"] == reporting.XG_REPORTING_PREVIEW_BLOCKED_MISSING_XG
    assert summary["rows_missing_xg"] == 1
    assert summary["reporting_output_path"] == ""


def test_blocks_unsafe_output_path(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    summary = reporting.build_xg_reporting_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "not_outputs",
        base_dir=root,
    )

    assert summary["reporting_status"] == reporting.XG_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH


def test_does_not_modify_target_artifact_or_manifest(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    before = {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)}

    reporting.build_xg_reporting_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    assert {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)} == before


def test_audit_reporting_preview_ready(tmp_path):
    summary, _root, _xg, target, _manifest = _build(tmp_path)

    table, _markdown, rec = audit_reporting.run(
        preview=summary["reporting_output_path"],
        target=target,
        expected_rows=2,
        output_dir=tmp_path / "diag",
    )

    assert rec == audit_reporting.XG_REPORTING_PREVIEW_READY
    assert table.iloc[0]["missing_xg_rows"] == 0


def test_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)
    monkeypatch.setattr(helper, "TARGET", root / "data" / "processed" / "target_clean.csv")

    summary = helper.run_workflow(manifest, root / "outputs" / "xg_reporting_preview")

    assert summary["recommendation"] == audit_reporting.XG_REPORTING_PREVIEW_READY
    assert summary["rows_reported"] == 2


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}

    _build(tmp_path)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
