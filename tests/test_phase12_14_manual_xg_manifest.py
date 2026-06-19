# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.manual_xg_manifest import (
    REQUIRED_COLUMNS,
    evaluate_manifest_acceptance,
    load_manual_xg_manifest,
    validate_manual_xg_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_manual_xg_manifest as manifest_audit  # noqa: E402


MANIFEST_TEMPLATE = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _xg(rows: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "home_team": [f"Team {day}" for day in range(1, rows + 1)],
        "away_team": [f"Away {day}" for day in range(1, rows + 1)],
        "home_xg": [1.1] * rows,
        "away_xg": [0.8] * rows,
    })


def _target(rows: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "home_team": [f"Team {day}" for day in range(1, rows + 1)],
        "away_team": [f"Away {day}" for day in range(1, rows + 1)],
    })


def _write_manifest(path: Path, rows: list[dict[str, object]]) -> Path:
    pd.DataFrame(rows, columns=REQUIRED_COLUMNS).to_csv(path, index=False)
    return path


def _demo_row() -> dict[str, object]:
    return {
        "manifest_id": "demo",
        "xg_file_path": "data/examples/manual_xg_accepted_demo.csv",
        "target_file_path": "data/examples/manual_xg_acceptance_target_demo.csv",
        "league": "Demo League",
        "season": "2026",
        "source_type": "DEMO_ONLY",
        "data_role": "DEMO",
        "is_demo": "true",
        "expected_rows": 2,
        "min_join_coverage_pct": 95.0,
        "notes": "demo only",
    }


def test_manifest_template_exists_with_required_columns():
    table = pd.read_csv(MANIFEST_TEMPLATE)

    assert MANIFEST_TEMPLATE.exists()
    assert list(table.columns) == REQUIRED_COLUMNS


def test_demo_manifest_row_is_not_counted_as_production():
    table, summary = evaluate_manifest_acceptance(MANIFEST_TEMPLATE, base_dir=ROOT, include_demo=True)

    demo = table[table["manifest_id"] == "demo_manual_xg_acceptance"].iloc[0]
    assert demo["is_demo"] == True
    assert demo["production_accepted"] == False
    trusted = table[table["manifest_id"] == "trusted_xg_understat_bundesliga_2024_manual_xg"]
    if not trusted.empty:
        assert trusted.iloc[0]["production_accepted"] == True
        assert summary.accepted_production_entries == 1
    else:
        assert summary.accepted_production_entries == 0


def test_blank_production_placeholder_is_invalid_incomplete():
    table, _summary = evaluate_manifest_acceptance(MANIFEST_TEMPLATE, base_dir=ROOT)

    placeholder = table[table["manifest_id"] == "production_manual_xg_placeholder"].iloc[0]
    assert placeholder["entry_valid"] == False
    assert "MISSING_XG_FILE_PATH" in placeholder["entry_errors"]
    assert "MISSING_TARGET_FILE_PATH" in placeholder["entry_errors"]


def test_production_entry_without_paths_is_not_accepted(tmp_path):
    manifest = _write_manifest(tmp_path / "manifest.csv", [{
        **_demo_row(),
        "manifest_id": "bad_prod",
        "xg_file_path": "",
        "target_file_path": "",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
    }])

    table, summary = evaluate_manifest_acceptance(manifest, base_dir=tmp_path)

    assert table.iloc[0]["production_accepted"] == False
    assert summary.recommendation == "FIX_MANIFEST_ENTRIES"


def test_production_entry_with_valid_filled_xg_and_target_can_be_accepted(tmp_path):
    xg = tmp_path / "manual_xg.csv"
    target = tmp_path / "target.csv"
    _xg().to_csv(xg, index=False)
    _target().to_csv(target, index=False)
    manifest = _write_manifest(tmp_path / "manifest.csv", [{
        "manifest_id": "prod",
        "xg_file_path": "manual_xg.csv",
        "target_file_path": "target.csv",
        "league": "League",
        "season": "2026",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": 2,
        "min_join_coverage_pct": 95.0,
        "notes": "production test",
    }])

    table, summary = evaluate_manifest_acceptance(manifest, base_dir=tmp_path)

    assert table.iloc[0]["acceptance_label"] == "MANUAL_XG_ACCEPTED"
    assert table.iloc[0]["production_accepted"] == True
    assert summary.accepted_production_entries == 1


def test_accepted_production_entry_recommends_ready(tmp_path):
    xg = tmp_path / "manual_xg.csv"
    target = tmp_path / "target.csv"
    _xg().to_csv(xg, index=False)
    _target().to_csv(target, index=False)
    manifest = _write_manifest(tmp_path / "manifest.csv", [{
        "manifest_id": "prod",
        "xg_file_path": "manual_xg.csv",
        "target_file_path": "target.csv",
        "league": "League",
        "season": "2026",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": 2,
        "min_join_coverage_pct": 95.0,
        "notes": "production test",
    }])

    _table, summary = evaluate_manifest_acceptance(manifest, base_dir=tmp_path)

    assert summary.recommendation == "READY_FOR_MANUAL_XG_ENRICHMENT_PIPELINE"


def test_manifest_with_only_demo_template_entries_recommends_add_production(tmp_path):
    manifest = _write_manifest(tmp_path / "manifest.csv", [_demo_row()])

    _table, summary = evaluate_manifest_acceptance(manifest, base_dir=ROOT, include_demo=True)

    assert summary.recommendation == "ADD_PRODUCTION_MANUAL_XG_FILE"


def test_manifest_with_invalid_production_entries_recommends_fix_manifest(tmp_path):
    manifest = _write_manifest(tmp_path / "manifest.csv", [{
        **_demo_row(),
        "manifest_id": "bad_prod",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "xg_file_path": "",
        "target_file_path": "",
    }])

    _table, summary = evaluate_manifest_acceptance(manifest, base_dir=tmp_path)

    assert summary.recommendation == "FIX_MANIFEST_ENTRIES"


def test_audit_manual_xg_manifest_writes_csv_and_markdown(tmp_path):
    output_dir = tmp_path / "diagnostics"

    table, markdown = manifest_audit.run(
        manifest=MANIFEST_TEMPLATE,
        output_dir=output_dir,
        base_dir=ROOT,
        include_demo=True,
    )

    assert not table.empty
    assert (output_dir / manifest_audit.OUTPUT_CSV).exists()
    assert (output_dir / manifest_audit.OUTPUT_MD).exists()
    assert "Phase 12.14 is diagnostic/foundation only" in markdown


def test_markdown_says_demo_entries_never_counted_as_production(tmp_path):
    _table, markdown = manifest_audit.run(
        manifest=MANIFEST_TEMPLATE,
        output_dir=tmp_path / "diagnostics",
        base_dir=ROOT,
        include_demo=True,
    )

    assert "Demo entries are never counted as production manual xG" in markdown


def test_source_target_and_manifest_files_are_never_overwritten(tmp_path):
    xg = tmp_path / "manual_xg.csv"
    target = tmp_path / "target.csv"
    _xg().to_csv(xg, index=False)
    _target().to_csv(target, index=False)
    manifest = _write_manifest(tmp_path / "manifest.csv", [{
        "manifest_id": "prod",
        "xg_file_path": "manual_xg.csv",
        "target_file_path": "target.csv",
        "league": "League",
        "season": "2026",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": 2,
        "min_join_coverage_pct": 95.0,
        "notes": "production test",
    }])
    before = {path: _hash(path) for path in (xg, target, manifest)}

    evaluate_manifest_acceptance(manifest, base_dir=tmp_path, output_dir=tmp_path / "preview")

    assert {path: _hash(path) for path in (xg, target, manifest)} == before


def test_validate_manifest_summary_counts_template():
    summary = validate_manual_xg_manifest(MANIFEST_TEMPLATE, base_dir=ROOT)

    assert summary.entries_total >= 2
    assert summary.demo_entries == 1


def test_load_manifest_returns_entries():
    entries = load_manual_xg_manifest(MANIFEST_TEMPLATE)

    assert entries[0].manifest_id == "demo_manual_xg_acceptance"


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    manifest_audit.run(manifest=MANIFEST_TEMPLATE, output_dir=tmp_path / "diagnostics", base_dir=ROOT)

    assert {path: _hash(path) for path in protected} == before
