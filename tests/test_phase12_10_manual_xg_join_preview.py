# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.xg_join_preview import (
    JOIN_BLOCKED_DUPLICATE_KEYS,
    JOIN_LOW_COVERAGE,
    JOIN_NO_MATCHES,
    JOIN_READY,
    JOIN_READY_WITH_WARNINGS,
    preview_xg_join,
    run_xg_join_preview,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_manual_xg_join_readiness as join_audit  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _xg(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "home_team": [f"Team {day}" for day in range(1, rows + 1)],
        "away_team": [f"Away {day}" for day in range(1, rows + 1)],
        "home_xg": [1.0] * rows,
        "away_xg": [0.8] * rows,
    })


def _target(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "HomeTeam": [f"Team {day}" for day in range(1, rows + 1)],
        "AwayTeam": [f"Away {day}" for day in range(1, rows + 1)],
    })


def test_exact_date_home_away_keys_join_successfully():
    _joined, result = preview_xg_join(_xg(), _target())

    assert result.matched_rows == 3
    assert result.join_quality_label == JOIN_READY


def test_date_normalization_works_for_datetime_vs_date_only():
    xg = _xg()
    target = _target()
    target["Date"] = ["2026-01-01 20:30:00", "2026-01-02 12:00:00", "2026-01-03 18:00:00"]

    _joined, result = preview_xg_join(xg, target)

    assert result.matched_rows == 3


def test_team_normalization_is_applied_consistently():
    xg = _xg()
    target = _target()
    target["HomeTeam"] = [" team 1 ", "TEAM 2", "Team. 3"]

    _joined, result = preview_xg_join(xg, target)

    assert result.matched_rows == 3


def test_duplicate_xg_keys_block_join():
    xg = pd.concat([_xg(1), _xg(1)], ignore_index=True)

    _joined, result = preview_xg_join(xg, _target(1))

    assert result.join_quality_label == JOIN_BLOCKED_DUPLICATE_KEYS
    assert result.duplicate_xg_keys > 0


def test_duplicate_target_keys_block_join():
    target = pd.concat([_target(1), _target(1)], ignore_index=True)

    _joined, result = preview_xg_join(_xg(1), target)

    assert result.join_quality_label == JOIN_BLOCKED_DUPLICATE_KEYS
    assert result.duplicate_target_keys > 0


def test_no_matches_produce_join_no_matches():
    target = _target()
    target["HomeTeam"] = ["X", "Y", "Z"]

    _joined, result = preview_xg_join(_xg(), target)

    assert result.join_quality_label == JOIN_NO_MATCHES


def test_low_coverage_produces_low_coverage():
    target = _target(5)
    xg = _xg(1)

    _joined, result = preview_xg_join(xg, target)

    assert result.join_quality_label == JOIN_LOW_COVERAGE


def test_high_coverage_produces_ready_or_warning():
    target = _target(4)
    xg = _xg(3)

    _joined, result = preview_xg_join(xg, target)

    assert result.join_quality_label in {JOIN_READY, JOIN_READY_WITH_WARNINGS}


def test_preview_output_writes_only_under_outputs_dir(tmp_path):
    xg_path = tmp_path / "manual_xg.csv"
    target_path = tmp_path / "target.csv"
    _xg().to_csv(xg_path, index=False)
    _target().to_csv(target_path, index=False)
    output_dir = tmp_path / "outputs" / "xg_join_preview"

    result = run_xg_join_preview(xg_path, target_path, output_dir=output_dir)

    output = Path(result.output_path)
    assert output.exists()
    assert output_dir.resolve() in output.resolve().parents


def test_no_write_preview_does_not_write_output(tmp_path):
    xg_path = tmp_path / "manual_xg.csv"
    target_path = tmp_path / "target.csv"
    _xg().to_csv(xg_path, index=False)
    _target().to_csv(target_path, index=False)
    output_dir = tmp_path / "outputs" / "xg_join_preview"

    result = subprocess.run([
        sys.executable,
        str(ROOT / "scripts" / "preview_manual_xg_join.py"),
        "--xg",
        str(xg_path),
        "--target",
        str(target_path),
        "--output-dir",
        str(output_dir),
        "--no-write-preview",
    ], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert not output_dir.exists()


def test_source_and_target_are_never_overwritten(tmp_path):
    xg_path = tmp_path / "manual_xg.csv"
    target_path = tmp_path / "target.csv"
    _xg().to_csv(xg_path, index=False)
    _target().to_csv(target_path, index=False)
    before = {_hash(xg_path), _hash(target_path)}

    run_xg_join_preview(xg_path, target_path, output_dir=tmp_path / "outputs" / "xg_join_preview")

    assert before == {_hash(xg_path), _hash(target_path)}


def test_audit_manual_xg_join_readiness_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    templates = root / "data" / "templates"
    processed = root / "data" / "processed"
    templates.mkdir(parents=True)
    processed.mkdir(parents=True)
    _xg(2).to_csv(templates / "manual_xg_template.csv", index=False)
    _target(2).to_csv(processed / "real_matches_clean.csv", index=False)

    table, markdown = join_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert not table.empty
    assert (root / "outputs" / "diagnostics" / join_audit.OUTPUT_CSV).exists()
    assert "Phase 12.10 is diagnostic/foundation only" in markdown


def test_no_production_manual_xg_file_recommends_add_production_file(tmp_path):
    root = tmp_path / "repo"
    templates = root / "data" / "templates"
    processed = root / "data" / "processed"
    templates.mkdir(parents=True)
    processed.mkdir(parents=True)
    _xg(2).to_csv(templates / "manual_xg_template.csv", index=False)
    _target(2).to_csv(processed / "real_matches_clean.csv", index=False)

    table, _markdown = join_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert join_audit.recommendation(table) == "ADD_PRODUCTION_MANUAL_XG_FILE"


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    xg_path = tmp_path / "manual_xg.csv"
    target_path = tmp_path / "target.csv"
    _xg().to_csv(xg_path, index=False)
    _target().to_csv(target_path, index=False)

    run_xg_join_preview(xg_path, target_path, output_dir=tmp_path / "outputs" / "xg_join_preview")

    after = {path: _hash(path) for path in protected}
    assert after == before
