from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_manifest_xg_enrichment_preview as audit_preview  # noqa: E402
import build_manifest_xg_enrichment_preview as builder  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(tmp_path: Path, *, rows: int = 2, missing_xg: bool = False, xg_path: str | None = None) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    accepted = root / "data" / "trusted_xg_sources" / "accepted"
    processed = root / "data" / "processed"
    templates = root / "data" / "templates"
    accepted.mkdir(parents=True)
    processed.mkdir(parents=True)
    templates.mkdir(parents=True)
    xg_rel = xg_path or "data/trusted_xg_sources/accepted/tiny_manual_xg.csv"
    xg = root / xg_rel
    xg.parent.mkdir(parents=True, exist_ok=True)
    target = processed / "target_clean.csv"
    manifest = templates / "manual_xg_manifest_template.csv"
    pd.DataFrame([
        {
            "date": f"2024-01-{idx + 1:02d}",
            "home_team": f"Home {idx}",
            "away_team": f"Away {idx}",
            "home_xg": "" if missing_xg and idx == 0 else 1.1 + idx,
            "away_xg": 0.7 + idx,
        }
        for idx in range(rows)
    ]).to_csv(xg, index=False)
    pd.DataFrame([
        {
            "Date": f"2024-01-{idx + 1:02d}",
            "HomeTeam": f"Home {idx}",
            "AwayTeam": f"Away {idx}",
            "FTHG": idx,
            "FTAG": idx + 1,
            "FTR": "A",
        }
        for idx in range(rows)
    ]).to_csv(target, index=False)
    _write_manifest(manifest, xg_rel=xg_rel)
    return root, xg, target, manifest


def _write_manifest(
    manifest: Path,
    *,
    xg_rel: str = "data/trusted_xg_sources/accepted/tiny_manual_xg.csv",
    target_rel: str = "data/processed/target_clean.csv",
    manifest_id: str = "tiny_manifest_xg",
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
        "notes": "tiny fixture accepted xG",
    }]).to_csv(manifest, index=False)


def test_builds_enrichment_preview_from_accepted_manifest_entry(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        write_preview=True,
        base_dir=root,
    )

    assert summary["enrichment_status"] == builder.MANIFEST_XG_ENRICHMENT_PREVIEW_READY
    assert summary["rows_target"] == 2
    assert summary["rows_enriched"] == 2
    assert summary["rows_missing_xg"] == 0
    assert Path(summary["preview_output_path"]).exists()


def test_rejects_missing_accepted_artifact(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    (root / "data" / "trusted_xg_sources" / "accepted" / "tiny_manual_xg.csv").unlink()

    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        base_dir=root,
    )

    assert summary["enrichment_status"] == builder.MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_MISSING_ARTIFACT


def test_rejects_outputs_path_in_production_manifest_entry(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, xg_path="outputs/tiny_manual_xg.csv")

    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        base_dir=root,
    )

    assert summary["enrichment_status"] == builder.MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH


def test_rejects_unsafe_absolute_path(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    _write_manifest(manifest, xg_rel="C:/outside/tiny_manual_xg.csv")

    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        base_dir=root,
    )

    assert summary["enrichment_status"] == builder.MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH


def test_preserves_row_count_and_identity_columns(tmp_path):
    root, _xg, target, manifest = _fixture_root(tmp_path)
    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        write_preview=True,
        base_dir=root,
    )
    preview = pd.read_csv(summary["preview_output_path"], low_memory=False)
    target_df = pd.read_csv(target, low_memory=False)

    assert len(preview) == len(target_df)
    assert preview[["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]].equals(
        target_df[["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]]
    )


def test_fills_only_from_accepted_xg_artifact(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        write_preview=True,
        base_dir=root,
    )
    preview = pd.read_csv(summary["preview_output_path"], low_memory=False)
    artifact = pd.read_csv(xg, low_memory=False)

    assert preview[["home_xg", "away_xg"]].equals(artifact[["home_xg", "away_xg"]])


def test_does_not_infer_missing_xg(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, missing_xg=True)

    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        base_dir=root,
    )

    assert summary["enrichment_status"] == builder.MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_LOW_COVERAGE
    assert summary["rows_missing_xg"] == 1


def test_does_not_modify_target_artifact_or_manifest(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    before = {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)}

    builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        write_preview=True,
        base_dir=root,
    )

    assert {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)} == before


def test_audit_preview_ready_on_tiny_fixture(tmp_path):
    root, _xg, target, manifest = _fixture_root(tmp_path)
    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        write_preview=True,
        base_dir=root,
    )

    table, _markdown, rec = audit_preview.run(
        preview=summary["preview_output_path"],
        target=target,
        output_dir=tmp_path / "diag",
        expected_rows=2,
    )

    assert rec == audit_preview.MANIFEST_XG_ENRICHMENT_PREVIEW_READY
    assert table.iloc[0]["missing_xg_rows"] == 0


def test_helper_equivalent_workflow_works_on_tiny_fixture_data(tmp_path):
    root, _xg, target, manifest = _fixture_root(tmp_path)
    summary = builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        target="data/processed/target_clean.csv",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        write_preview=True,
        base_dir=root,
    )
    _table, _markdown, rec = audit_preview.run(
        preview=summary["preview_output_path"],
        target=target,
        output_dir=tmp_path / "diag",
        expected_rows=2,
    )

    assert summary["join_coverage_pct"] == 100.0
    assert rec == audit_preview.MANIFEST_XG_ENRICHMENT_PREVIEW_READY


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    builder.build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id="tiny_manifest_xg",
        output_dir=root / "outputs" / "xg_enrichment_preview",
        write_preview=True,
        base_dir=root,
    )

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
