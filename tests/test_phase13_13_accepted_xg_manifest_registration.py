from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import audit_accepted_xg_manifest_registration as audit_registration  # noqa: E402
import register_accepted_xg_manifest_entry as register_script  # noqa: E402
from football_prediction_v19.importers.manual_xg_manifest import REQUIRED_COLUMNS  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(tmp_path: Path, *, rows: int = 2) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    accepted = root / "data" / "trusted_xg_sources" / "accepted"
    processed = root / "data" / "processed"
    templates = root / "data" / "templates"
    accepted.mkdir(parents=True)
    processed.mkdir(parents=True)
    templates.mkdir(parents=True)
    xg = accepted / "tiny_manual_xg.csv"
    target = processed / "target_clean.csv"
    manifest = templates / "manual_xg_manifest_template.csv"
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
        for idx in range(rows)
    ]).to_csv(target, index=False)
    pd.DataFrame(columns=REQUIRED_COLUMNS).to_csv(manifest, index=False)
    return root, xg, target, manifest


def _preview(path: Path, xg_rel: str, target_rel: str, *, league: str = "Bundesliga", season: str = "2024") -> Path:
    pd.DataFrame([{
        "manifest_id": "tiny_accepted_xg",
        "xg_file_path": xg_rel,
        "target_file_path": target_rel,
        "league": league,
        "season": season,
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": 2,
        "min_join_coverage_pct": 100.0,
        "notes": "test accepted artifact",
    }]).to_csv(path, index=False)
    return path


def test_dry_run_does_not_modify_production_manifest(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "data/trusted_xg_sources/accepted/tiny_manual_xg.csv", "data/processed/target_clean.csv")
    before = _sha(manifest)

    summary = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert summary["registration_status"] == register_script.ACCEPTED_XG_MANIFEST_ENTRY_READY
    assert _sha(manifest) == before


def test_write_registers_accepted_artifact_idempotently(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "data/trusted_xg_sources/accepted/tiny_manual_xg.csv", "data/processed/target_clean.csv")

    first = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
        write=True,
    )
    second = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
        write=True,
    )
    table = pd.read_csv(manifest, keep_default_na=False)

    assert first["registration_status"] == register_script.ACCEPTED_XG_MANIFEST_ENTRY_WRITTEN
    assert second["registration_status"] == register_script.ACCEPTED_XG_MANIFEST_ENTRY_ALREADY_REGISTERED
    assert len(table[table["manifest_id"] == "tiny_accepted_xg"]) == 1


def test_outputs_path_is_rejected(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "outputs/tiny_manual_xg.csv", "data/processed/target_clean.csv")

    summary = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert summary["registration_status"] == register_script.ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_INVALID_PATH


def test_absolute_windows_path_is_rejected(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "C:/outside/tiny_manual_xg.csv", "data/processed/target_clean.csv")

    summary = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert summary["registration_status"] == register_script.ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_INVALID_PATH


def test_missing_league_or_season_is_rejected(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(
        tmp_path / "preview.csv",
        "data/trusted_xg_sources/accepted/tiny_manual_xg.csv",
        "data/processed/target_clean.csv",
        league="",
        season="",
    )

    summary = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert summary["registration_status"] == register_script.ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_MISSING_METADATA


def test_missing_artifact_is_rejected(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "data/trusted_xg_sources/accepted/missing.csv", "data/processed/target_clean.csv")

    summary = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert summary["registration_status"] == register_script.ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_INVALID_PATH


def test_registered_artifact_validates_rows_and_full_coverage_in_tiny_fixture(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "data/trusted_xg_sources/accepted/tiny_manual_xg.csv", "data/processed/target_clean.csv")

    summary = register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert summary["rows_source"] == 2
    assert summary["join_coverage_pct"] == 100.0


def test_source_and_target_csvs_are_not_modified(tmp_path):
    root, xg, target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "data/trusted_xg_sources/accepted/tiny_manual_xg.csv", "data/processed/target_clean.csv")
    before = {xg: _sha(xg), target: _sha(target)}

    register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
        write=True,
    )

    assert {xg: _sha(xg), target: _sha(target)} == before


def test_no_xg_values_inferred_or_invented(tmp_path):
    root, xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "data/trusted_xg_sources/accepted/tiny_manual_xg.csv", "data/processed/target_clean.csv")
    original = pd.read_csv(xg, low_memory=False)

    register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
        write=True,
    )

    assert pd.read_csv(xg, low_memory=False).equals(original)


def test_audit_confirms_registered_default_artifact(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path, rows=2)
    default_xg = root / register_script.DEFAULT_ENTRY["xg_file_path"]
    default_target = root / register_script.DEFAULT_ENTRY["target_file_path"]
    default_xg.parent.mkdir(parents=True, exist_ok=True)
    default_target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "A", "away_team": "B", "home_xg": 1.0, "away_xg": 0.8},
        {"date": "2024-01-02", "home_team": "C", "away_team": "D", "home_xg": 1.2, "away_xg": 0.6},
    ]).to_csv(default_xg, index=False)
    pd.DataFrame([
        {"Date": "2024-01-01", "HomeTeam": "A", "AwayTeam": "B"},
        {"Date": "2024-01-02", "HomeTeam": "C", "AwayTeam": "D"},
    ]).to_csv(default_target, index=False)
    entry = {**register_script.DEFAULT_ENTRY, "expected_rows": 2}
    pd.DataFrame([entry], columns=REQUIRED_COLUMNS).to_csv(manifest, index=False)

    table, _markdown, rec = audit_registration.audit_accepted_xg_manifest_registration(
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert rec == audit_registration.ACCEPTED_XG_MANIFEST_REGISTERED
    assert table.iloc[0]["join_coverage_pct"] == 100.0


def test_audit_writes_csv_and_markdown(tmp_path):
    root, _xg, _target, manifest = _fixture_root(tmp_path)

    _table, markdown, _rec = audit_registration.audit_accepted_xg_manifest_registration(
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
    )

    assert (tmp_path / "diag" / audit_registration.OUTPUT_CSV).exists()
    assert (tmp_path / "diag" / audit_registration.OUTPUT_MD).exists()
    assert "xG remains inactive" in markdown


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, _xg, _target, manifest = _fixture_root(tmp_path)
    preview = _preview(tmp_path / "preview.csv", "data/trusted_xg_sources/accepted/tiny_manual_xg.csv", "data/processed/target_clean.csv")

    register_script.register_accepted_xg_manifest_entry(
        manifest_entry_preview=preview,
        manifest=manifest,
        base_dir=root,
        output_dir=tmp_path / "diag",
        write=True,
    )

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
