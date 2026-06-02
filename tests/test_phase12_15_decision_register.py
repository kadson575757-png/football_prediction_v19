# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import write_phase12_decision_register as register  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_script_writes_csv_and_markdown(tmp_path):
    table, markdown = register.run(output_dir=tmp_path)

    assert not table.empty
    assert (tmp_path / register.OUTPUT_CSV).exists()
    assert (tmp_path / register.OUTPUT_MD).exists()
    assert "Phase 12 Decision Register" in markdown


def test_csv_includes_phases_12_1_through_12_15(tmp_path):
    table, _markdown = register.run(output_dir=tmp_path)

    expected = [f"12.{idx}" for idx in range(1, 16)]
    assert list(table["phase_id"]) == expected


def test_markdown_includes_complete_foundation_status(tmp_path):
    _table, markdown = register.run(output_dir=tmp_path)

    assert "COMPLETE_FOR_FOUNDATION_LAYER" in markdown


def test_markdown_includes_do_not_use_xg_in_model_yet(tmp_path):
    _table, markdown = register.run(output_dir=tmp_path)

    assert "DO_NOT_USE_XG_IN_MODEL_YET" in markdown


def test_markdown_requires_accepted_production_manual_xg_before_enrichment(tmp_path):
    _table, markdown = register.run(output_dir=tmp_path)

    assert "REQUIRE_ACCEPTED_PRODUCTION_MANUAL_XG_BEFORE_ENRICHMENT" in markdown


def test_markdown_includes_no_probability_logic_change(tmp_path):
    _table, markdown = register.run(output_dir=tmp_path)

    assert "No probability logic changes" in markdown
    assert "DO_NOT_CHANGE_PROBABILITY_OR_MARKET_LOGIC" in markdown


def test_markdown_includes_no_betting_staking_roi_change(tmp_path):
    _table, markdown = register.run(output_dir=tmp_path)

    assert "No betting/staking/ROI changes" in markdown


def test_markdown_includes_no_super_a_tier_activation(tmp_path):
    _table, markdown = register.run(output_dir=tmp_path)

    assert "No SUPER_A_TIER activation" in markdown


def test_final_recommendation_exact_value(tmp_path):
    _table, markdown = register.run(output_dir=tmp_path)

    assert register.FINAL_RECOMMENDATION in markdown
    assert markdown.strip().endswith(register.FINAL_RECOMMENDATION)


def test_csv_has_required_fields(tmp_path):
    table, _markdown = register.run(output_dir=tmp_path)
    expected = {
        "phase_id",
        "phase_name",
        "purpose",
        "key_outputs",
        "key_result",
        "final_decision",
        "production_data_created",
        "model_logic_changed",
        "next_dependency",
    }

    assert expected.issubset(table.columns)
    assert set(table["model_logic_changed"]) == {"no"}


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    register.run(output_dir=tmp_path)

    assert {path: _hash(path) for path in protected} == before


def test_written_csv_can_be_read_back(tmp_path):
    register.run(output_dir=tmp_path)

    table = pd.read_csv(tmp_path / register.OUTPUT_CSV)

    assert len(table) == 15
    assert str(table.iloc[-1]["phase_id"]) == "12.15"
