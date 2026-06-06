# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.trusted_xg_manifest_promotion import (
    TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE,
    TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE,
    TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG,
    TRUSTED_XG_PROMOTION_READY,
    TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS,
    run_trusted_xg_manifest_promotion,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_trusted_xg_manifest_promotion as promotion_audit  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _xg(rows: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "home_team": [f"Team {day}" for day in range(1, rows + 1)],
        "away_team": [f"Away {day}" for day in range(1, rows + 1)],
        "home_xg": [1.0 + day / 10 for day in range(1, rows + 1)],
        "away_xg": [0.8 + day / 10 for day in range(1, rows + 1)],
    })


def _target(rows: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "home_team": [f"Team {day}" for day in range(1, rows + 1)],
        "away_team": [f"Away {day}" for day in range(1, rows + 1)],
    })


def _write_pair(tmp_path: Path, xg_rows: int = 2, target_rows: int = 2) -> tuple[Path, Path]:
    source = tmp_path / "trusted_xg.csv"
    target = tmp_path / "target.csv"
    _xg(xg_rows).to_csv(source, index=False)
    _target(target_rows).to_csv(target, index=False)
    return source, target


def test_valid_trusted_xg_source_and_target_produces_ready(tmp_path):
    source, target = _write_pair(tmp_path)

    result = run_trusted_xg_manifest_promotion(source, target, target, output_dir=tmp_path / "outputs" / "xg_promotion_preview")

    assert result.promotion_label == TRUSTED_XG_PROMOTION_READY
    assert result.acceptance_label == "MANUAL_XG_ACCEPTED"


def test_promotion_writes_filled_preview_under_outputs(tmp_path):
    source, target = _write_pair(tmp_path)
    output_dir = tmp_path / "outputs" / "xg_promotion_preview"

    result = run_trusted_xg_manifest_promotion(source, target, target, output_dir=output_dir)

    filled = Path(result.filled_preview_path)
    assert filled.exists()
    assert output_dir.resolve() in filled.resolve().parents


def test_promotion_writes_manifest_entry_preview_under_outputs(tmp_path):
    source, target = _write_pair(tmp_path)
    output_dir = tmp_path / "outputs" / "xg_promotion_preview"

    result = run_trusted_xg_manifest_promotion(source, target, target, output_dir=output_dir)

    manifest = Path(result.manifest_preview_path)
    assert manifest.exists()
    assert output_dir.resolve() in manifest.resolve().parents
    table = pd.read_csv(manifest)
    assert table.iloc[0]["source_type"] == "MANUAL_XG_CSV"
    assert table.iloc[0]["data_role"] == "PRODUCTION"


def test_source_xg_file_is_never_overwritten(tmp_path):
    source, target = _write_pair(tmp_path)
    before = _hash(source)

    run_trusted_xg_manifest_promotion(source, target, target, output_dir=tmp_path / "outputs" / "xg_promotion_preview")

    assert _hash(source) == before


def test_target_file_is_never_overwritten(tmp_path):
    source, target = _write_pair(tmp_path)
    before = _hash(target)

    run_trusted_xg_manifest_promotion(source, target, target, output_dir=tmp_path / "outputs" / "xg_promotion_preview")

    assert _hash(target) == before


def test_manifest_template_is_never_overwritten(tmp_path):
    source, target = _write_pair(tmp_path)
    manifest_template = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"
    before = _hash(manifest_template)

    run_trusted_xg_manifest_promotion(source, target, target, output_dir=tmp_path / "outputs" / "xg_promotion_preview")

    assert _hash(manifest_template) == before


def test_missing_xg_after_fill_blocks_promotion(tmp_path):
    source, target = _write_pair(tmp_path, xg_rows=1, target_rows=2)

    result = run_trusted_xg_manifest_promotion(source, target, target, output_dir=tmp_path / "outputs" / "xg_promotion_preview")

    assert result.promotion_label == TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG
    assert result.rows_missing_xg == 1


def test_invalid_trusted_xg_source_blocks_promotion(tmp_path):
    source = tmp_path / "bad_xg.csv"
    target = tmp_path / "target.csv"
    pd.DataFrame({"date": ["2026-01-01"], "home_team": ["A"]}).to_csv(source, index=False)
    _target(1).to_csv(target, index=False)

    result = run_trusted_xg_manifest_promotion(source, target, target, output_dir=tmp_path / "outputs" / "xg_promotion_preview")

    assert result.promotion_label == TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE


def test_low_join_coverage_blocks_promotion(tmp_path):
    source, template_source = _write_pair(tmp_path, xg_rows=2, target_rows=2)
    target = tmp_path / "large_target.csv"
    _target(5).to_csv(target, index=False)

    result = run_trusted_xg_manifest_promotion(
        source,
        template_source,
        target,
        output_dir=tmp_path / "outputs" / "xg_promotion_preview",
        min_join_coverage=70.0,
    )

    assert result.promotion_label == TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE


def test_accepted_with_warnings_produces_ready_with_warnings(tmp_path):
    source, template_source = _write_pair(tmp_path, xg_rows=3, target_rows=3)
    target = tmp_path / "target_4.csv"
    _target(4).to_csv(target, index=False)

    result = run_trusted_xg_manifest_promotion(
        source,
        template_source,
        target,
        output_dir=tmp_path / "outputs" / "xg_promotion_preview",
        min_join_coverage=70.0,
    )

    assert result.promotion_label == TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS


def test_cli_prints_promotion_label(tmp_path):
    source, target = _write_pair(tmp_path)
    result = subprocess.run([
        sys.executable,
        str(ROOT / "scripts" / "promote_trusted_xg_to_manifest.py"),
        "--source-xg",
        str(source),
        "--template-source",
        str(target),
        "--target",
        str(target),
        "--output-dir",
        str(tmp_path / "outputs" / "xg_promotion_preview"),
    ], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert "promotion_label=TRUSTED_XG_PROMOTION_READY" in result.stdout


def test_audit_trusted_xg_manifest_promotion_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    processed = root / "data" / "processed"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    _xg(2).to_csv(raw / "trusted_xg.csv", index=False)
    _target(2).to_csv(processed / "matches_clean.csv", index=False)

    table, markdown = promotion_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert not table.empty
    assert (root / "outputs" / "diagnostics" / promotion_audit.OUTPUT_CSV).exists()
    assert (root / "outputs" / "diagnostics" / promotion_audit.OUTPUT_MD).exists()
    assert "Phase 13.2 is diagnostic/foundation only" in markdown


def test_audit_recommendation_ready_when_promotion_ready_preview_exists(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    processed = root / "data" / "processed"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    _xg(2).to_csv(raw / "trusted_xg.csv", index=False)
    _target(2).to_csv(processed / "matches_clean.csv", index=False)

    table, _markdown = promotion_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert promotion_audit.recommendation(table) == "READY_TO_ADD_PRODUCTION_XG_MANIFEST_ENTRY"


def test_audit_recommendation_add_source_when_no_candidates(tmp_path):
    root = tmp_path / "repo"
    (root / "data" / "processed").mkdir(parents=True)
    _target(2).to_csv(root / "data" / "processed" / "matches_clean.csv", index=False)

    table, _markdown = promotion_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert promotion_audit.recommendation(table) == "ADD_TRUSTED_XG_SOURCE_FILE"


def test_docs_contain_trusted_xg_promotion_preview():
    text = (ROOT / "docs" / "manual_xg_workflow.md").read_text(encoding="utf-8")

    assert "Trusted xG Promotion Preview" in text
    assert "manifest is not modified automatically" in text


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    source, target = _write_pair(tmp_path)

    run_trusted_xg_manifest_promotion(source, target, target, output_dir=tmp_path / "outputs" / "xg_promotion_preview")

    assert {path: _hash(path) for path in protected} == before
