# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.manual_xg_acceptance import (
    MANUAL_XG_ACCEPTED,
    MANUAL_XG_NO_TARGET_PROVIDED,
    MANUAL_XG_REJECTED_DUPLICATE_KEYS,
    MANUAL_XG_REJECTED_INVALID_SCHEMA,
    MANUAL_XG_REJECTED_INVALID_VALUES,
    MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE,
    MANUAL_XG_REJECTED_MISSING_VALUES,
    MANUAL_XG_TEMPLATE_ONLY,
    evaluate_manual_xg_acceptance,
    run_manual_xg_acceptance_gate,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_filled_manual_xg_acceptance as acceptance_audit  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _xg(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "home_team": [f"Team {day}" for day in range(1, rows + 1)],
        "away_team": [f"Away {day}" for day in range(1, rows + 1)],
        "home_xg": [1.1] * rows,
        "away_xg": [0.8] * rows,
    })


def _target(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "HomeTeam": [f"Team {day}" for day in range(1, rows + 1)],
        "AwayTeam": [f"Away {day}" for day in range(1, rows + 1)],
    })


def test_valid_filled_manual_xg_with_matching_target_is_accepted():
    _joined, result = evaluate_manual_xg_acceptance(_xg(), target_df=_target())

    assert result.acceptance_label == MANUAL_XG_ACCEPTED
    assert result.rows_join_matched == 3
    assert result.join_coverage_pct == 100.0


def test_valid_filled_manual_xg_without_target_is_no_target_provided():
    _joined, result = evaluate_manual_xg_acceptance(_xg())

    assert result.acceptance_label == MANUAL_XG_NO_TARGET_PROVIDED


def test_blank_template_is_template_only():
    df = _xg()
    df["home_xg"] = pd.NA
    df["away_xg"] = pd.NA
    df["xg_entry_status"] = "NEEDS_MANUAL_ENTRY"

    _joined, result = evaluate_manual_xg_acceptance(df, source_path="manual_xg_template.csv")

    assert result.acceptance_label == MANUAL_XG_TEMPLATE_ONLY


def test_missing_xg_values_reject_missing_values():
    df = _xg()
    df.loc[0, "home_xg"] = pd.NA

    _joined, result = evaluate_manual_xg_acceptance(df, target_df=_target())

    assert result.acceptance_label == MANUAL_XG_REJECTED_MISSING_VALUES
    assert result.missing_xg_count == 1


def test_non_numeric_xg_values_reject_invalid_values():
    df = _xg()
    df["home_xg"] = df["home_xg"].astype(object)
    df.loc[0, "home_xg"] = "abc"

    _joined, result = evaluate_manual_xg_acceptance(df, target_df=_target())

    assert result.acceptance_label == MANUAL_XG_REJECTED_INVALID_VALUES
    assert result.non_numeric_xg_count == 1


def test_negative_xg_values_reject_invalid_values():
    df = _xg()
    df.loc[0, "away_xg"] = -0.1

    _joined, result = evaluate_manual_xg_acceptance(df, target_df=_target())

    assert result.acceptance_label == MANUAL_XG_REJECTED_INVALID_VALUES
    assert result.negative_xg_count == 1


def test_duplicate_match_keys_reject_duplicate_keys():
    df = pd.concat([_xg(1), _xg(1)], ignore_index=True)

    _joined, result = evaluate_manual_xg_acceptance(df, target_df=_target(1))

    assert result.acceptance_label == MANUAL_XG_REJECTED_DUPLICATE_KEYS
    assert result.duplicate_key_count > 0


def test_missing_identity_columns_reject_invalid_schema():
    df = pd.DataFrame({"home_xg": [1.0], "away_xg": [0.8]})

    _joined, result = evaluate_manual_xg_acceptance(df, target_df=_target(1))

    assert result.acceptance_label == MANUAL_XG_REJECTED_INVALID_SCHEMA


def test_low_join_coverage_rejects_low_join_coverage():
    target = _target(5)

    _joined, result = evaluate_manual_xg_acceptance(_xg(1), target_df=target, min_join_coverage=95.0)

    assert result.acceptance_label == MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE


def test_acceptance_preview_writes_only_under_outputs_preview(tmp_path):
    xg_path = tmp_path / "manual_xg.csv"
    target_path = tmp_path / "target.csv"
    _xg().to_csv(xg_path, index=False)
    _target().to_csv(target_path, index=False)
    output_dir = tmp_path / "outputs" / "xg_acceptance_preview"

    result = run_manual_xg_acceptance_gate(xg_path, target_path=target_path, output_dir=output_dir)

    output = Path(result.preview_output_path)
    assert output.exists()
    assert output_dir.resolve() in output.resolve().parents


def test_no_write_preview_does_not_write_output(tmp_path):
    xg_path = tmp_path / "manual_xg.csv"
    target_path = tmp_path / "target.csv"
    _xg().to_csv(xg_path, index=False)
    _target().to_csv(target_path, index=False)
    output_dir = tmp_path / "outputs" / "xg_acceptance_preview"

    completed = subprocess.run([
        sys.executable,
        str(ROOT / "scripts" / "validate_filled_manual_xg.py"),
        "--xg",
        str(xg_path),
        "--target",
        str(target_path),
        "--output-dir",
        str(output_dir),
        "--no-write-preview",
    ], capture_output=True, text=True, check=False)

    assert completed.returncode == 0
    assert "acceptance_label=MANUAL_XG_ACCEPTED" in completed.stdout
    assert not output_dir.exists()


def test_source_and_target_files_are_never_overwritten(tmp_path):
    xg_path = tmp_path / "manual_xg.csv"
    target_path = tmp_path / "target.csv"
    _xg().to_csv(xg_path, index=False)
    _target().to_csv(target_path, index=False)
    before = {_hash(xg_path), _hash(target_path)}

    run_manual_xg_acceptance_gate(xg_path, target_path=target_path, output_dir=tmp_path / "outputs" / "xg_acceptance_preview")

    assert before == {_hash(xg_path), _hash(target_path)}


def test_audit_filled_manual_xg_acceptance_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    manual = root / "data" / "manual_xg"
    processed = root / "data" / "processed"
    manual.mkdir(parents=True)
    processed.mkdir(parents=True)
    _xg().to_csv(manual / "season_manual_xg.csv", index=False)
    _target().to_csv(processed / "matches_clean_with_totals.csv", index=False)

    table, markdown = acceptance_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert not table.empty
    assert (root / "outputs" / "diagnostics" / acceptance_audit.OUTPUT_CSV).exists()
    assert (root / "outputs" / "diagnostics" / acceptance_audit.OUTPUT_MD).exists()
    assert "Phase 12.12 is diagnostic/foundation only" in markdown


def test_recommendation_fill_template_values_when_only_templates_exist(tmp_path):
    root = tmp_path / "repo"
    templates = root / "data" / "templates"
    templates.mkdir(parents=True)
    df = _xg()
    df["home_xg"] = pd.NA
    df["away_xg"] = pd.NA
    df["xg_entry_status"] = "NEEDS_MANUAL_ENTRY"
    df.to_csv(templates / "manual_xg_template.csv", index=False)

    table, _markdown = acceptance_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert acceptance_audit.recommendation(table) == "FILL_MANUAL_XG_TEMPLATE_VALUES"


def test_recommendation_ready_when_accepted_file_exists(tmp_path):
    root = tmp_path / "repo"
    manual = root / "data" / "manual_xg"
    processed = root / "data" / "processed"
    manual.mkdir(parents=True)
    processed.mkdir(parents=True)
    _xg().to_csv(manual / "season_manual_xg.csv", index=False)
    _target().to_csv(processed / "matches_clean_with_totals.csv", index=False)

    table, _markdown = acceptance_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert acceptance_audit.recommendation(table) == "READY_FOR_MANUAL_XG_ENRICHMENT_PIPELINE"


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

    run_manual_xg_acceptance_gate(xg_path, target_path=target_path, output_dir=tmp_path / "outputs" / "xg_acceptance_preview")

    assert {path: _hash(path) for path in protected} == before
