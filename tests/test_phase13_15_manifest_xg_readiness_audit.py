from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_manifest_xg_readiness as readiness  # noqa: E402
import build_understat_bundesliga_2024_xg_readiness_report as helper  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(
    tmp_path: Path,
    *,
    rows: int = 2,
    target_rows: int | None = None,
    xg_rel: str = "data/trusted_xg_sources/accepted/tiny_manual_xg.csv",
    target_rel: str = "data/processed/target_clean.csv",
    manifest_id: str = "tiny_manifest_xg",
) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    xg = root / xg_rel
    target = root / target_rel
    manifest = root / "data" / "templates" / "manual_xg_manifest_template.csv"
    xg.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {
            "date": f"2024-01-{idx + 1:02d}",
            "home_team": f"Home {idx}",
            "away_team": f"Away {idx}",
            "home_xg": 1.1 + idx,
            "away_xg": 0.7 + idx,
        }
        for idx in range(rows)
    ]).to_csv(xg, index=False)
    pd.DataFrame([
        {"Date": f"2024-01-{idx + 1:02d}", "HomeTeam": f"Home {idx}", "AwayTeam": f"Away {idx}"}
        for idx in range(target_rows if target_rows is not None else rows)
    ]).to_csv(target, index=False)
    _write_manifest(manifest, manifest_id=manifest_id, xg_rel=xg_rel, target_rel=target_rel, expected_rows=rows)
    return root, xg, target, manifest


def _write_manifest(
    manifest: Path,
    *,
    manifest_id: str = "tiny_manifest_xg",
    xg_rel: str = "data/trusted_xg_sources/accepted/tiny_manual_xg.csv",
    target_rel: str = "data/processed/target_clean.csv",
    expected_rows: int = 2,
) -> None:
    pd.DataFrame([{
        "manifest_id": manifest_id,
        "xg_file_path": xg_rel,
        "target_file_path": target_rel,
        "league": "Tiny League",
        "season": "2024",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": expected_rows,
        "min_join_coverage_pct": 100.0,
        "notes": "tiny accepted xG",
    }]).to_csv(manifest, index=False)


def test_accepted_manifest_entry_is_detected(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    table, _markdown, rec = readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert rec == readiness.MANIFEST_XG_READINESS_READY
    assert table.iloc[0]["manifest_id"] == "tiny_manifest_xg"


def test_readiness_audit_reaches_ready_for_tiny_fixture(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    table, _markdown, rec = readiness.run(manifest=manifest, manifest_id="tiny_manifest_xg", output_dir=tmp_path / "diag", base_dir=root)

    assert rec == readiness.MANIFEST_XG_READINESS_READY
    assert table.iloc[0]["readiness_status"] == readiness.MANIFEST_XG_READY_FOR_REPORTING_PREVIEW
    assert table.iloc[0]["model_integration_status"] == readiness.XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN


def test_missing_artifact_is_blocked(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    xg.unlink()

    table, _markdown, rec = readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert rec == readiness.FIX_MANIFEST_XG_READINESS
    assert table.iloc[0]["readiness_status"] == readiness.MANIFEST_XG_BLOCKED_MISSING_ARTIFACT


def test_missing_target_is_blocked(tmp_path):
    root, _xg, target, manifest = _fixture_root(tmp_path)
    target.unlink()

    table, _markdown, _rec = readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert table.iloc[0]["readiness_status"] == readiness.MANIFEST_XG_BLOCKED_MISSING_TARGET


def test_outputs_path_is_rejected(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, xg_rel="outputs/tiny_manual_xg.csv")

    table, _markdown, _rec = readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert table.iloc[0]["readiness_status"] == readiness.MANIFEST_XG_BLOCKED_UNSAFE_PATH


def test_unsafe_absolute_windows_path_is_rejected(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    _write_manifest(manifest, xg_rel="C:/outside/tiny_manual_xg.csv")

    table, _markdown, _rec = readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert table.iloc[0]["readiness_status"] == readiness.MANIFEST_XG_BLOCKED_UNSAFE_PATH


def test_low_coverage_is_blocked(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, rows=1, target_rows=2)

    table, _markdown, _rec = readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert table.iloc[0]["readiness_status"] == readiness.MANIFEST_XG_BLOCKED_LOW_COVERAGE


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    before = pd.read_csv(xg, low_memory=False)

    readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert pd.read_csv(xg, low_memory=False).equals(before)


def test_target_artifact_and_manifest_are_not_modified(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    before = {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)}

    readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)} == before


def test_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _xg, _target, manifest = _fixture_root(
        tmp_path,
        manifest_id=helper.MANIFEST_ID,
        xg_rel="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        target_rel="data/processed/football_data_D1_2024_clean.csv",
    )
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_report(manifest, tmp_path / "diag")

    assert summary["recommendation"] == readiness.MANIFEST_XG_READINESS_READY
    assert summary["readiness_status"] == readiness.MANIFEST_XG_READY_FOR_REPORTING_PREVIEW


def test_report_files_are_written(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    table, markdown, _rec = readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert not table.empty
    assert (tmp_path / "diag" / readiness.OUTPUT_CSV).exists()
    assert (tmp_path / "diag" / readiness.OUTPUT_MD).exists()
    assert "ADD_MANUAL_XG_VALUES" in markdown


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    readiness.run(manifest=manifest, output_dir=tmp_path / "diag", base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
