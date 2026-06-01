# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.manual_xg_acceptance import MANUAL_XG_ACCEPTED, run_manual_xg_acceptance_gate


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_filled_manual_xg_acceptance as acceptance_audit  # noqa: E402
import demo_manual_xg_acceptance as demo_script  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


DEMO_XG = ROOT / "data" / "examples" / "manual_xg_accepted_demo.csv"
DEMO_TARGET = ROOT / "data" / "examples" / "manual_xg_acceptance_target_demo.csv"
DOC = ROOT / "docs" / "manual_xg_workflow.md"


def test_demo_manual_xg_file_is_accepted_with_demo_target():
    result = run_manual_xg_acceptance_gate(DEMO_XG, target_path=DEMO_TARGET, write_preview=False)

    assert result.acceptance_label == MANUAL_XG_ACCEPTED
    assert result.rows_valid == 2
    assert result.rows_invalid == 0


def test_demo_acceptance_coverage_is_100_percent():
    result = run_manual_xg_acceptance_gate(DEMO_XG, target_path=DEMO_TARGET, write_preview=False)

    assert result.rows_join_matched == 2
    assert result.join_coverage_pct == 100.0


def test_demo_values_are_not_treated_as_production_by_broad_acceptance_audit():
    table = acceptance_audit.build_table(ROOT)

    assert "manual_xg_accepted_demo.csv" not in set(table["xg_file_name"].astype(str))


def test_demo_script_writes_csv_and_markdown(tmp_path):
    table, markdown = demo_script.run(root=ROOT, output_dir=tmp_path / "diagnostics")

    assert table.iloc[0]["acceptance_label"] == MANUAL_XG_ACCEPTED
    assert (tmp_path / "diagnostics" / demo_script.OUTPUT_CSV).exists()
    assert (tmp_path / "diagnostics" / demo_script.OUTPUT_MD).exists()
    assert "fake demo xG values" in markdown


def test_demo_markdown_includes_fake_demo_caveat(tmp_path):
    _table, markdown = demo_script.run(root=ROOT, output_dir=tmp_path / "diagnostics")

    assert "not real match xG values" in markdown
    assert "must not be used as production data" in markdown


def test_manual_xg_workflow_doc_exists_and_contains_safety_statements():
    text = DOC.read_text(encoding="utf-8")

    assert "Demo values are fake and not real xG" in text
    assert "The model does not use manual xG yet" in text
    assert "xG values are never inferred or invented" in text
    assert "Manual xG files must pass acceptance" in text
    assert "Empty xG placeholders do not increase confidence or recommendations" in text
    assert "No betting, staking, ROI, probability" in text


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    demo_script.run(root=ROOT, output_dir=tmp_path / "diagnostics")

    assert {path: _hash(path) for path in protected} == before


def test_demo_csv_declares_demo_only_source_type():
    df = pd.read_csv(DEMO_XG)

    assert set(df["xg_source_type"]) == {"DEMO_ONLY"}
