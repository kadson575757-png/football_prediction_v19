# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import write_phase11_decision_register as register  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_decision_register_markdown_is_written(tmp_path):
    _df, markdown = register.run(tmp_path)

    assert (tmp_path / register.OUTPUT_MD).exists()
    assert "# Phase 11 Decision Register" in markdown


def test_decision_register_csv_is_written(tmp_path):
    df, _markdown = register.run(tmp_path)

    assert (tmp_path / register.OUTPUT_CSV).exists()
    assert len(df) == 7


def test_final_recommendation_contains_keep_phase11_3_defensive_rules(tmp_path):
    _df, markdown = register.run(tmp_path)

    assert "KEEP_PHASE_11_3_DEFENSIVE_RULES" in markdown


def test_final_recommendation_contains_do_not_relax_ligue1(tmp_path):
    _df, markdown = register.run(tmp_path)

    assert "DO_NOT_RELAX_LIGUE1" in markdown


def test_report_says_super_a_tier_remains_inactive(tmp_path):
    _df, markdown = register.run(tmp_path)

    assert "SUPER_A_TIER remains inactive" in markdown
    assert "DO_NOT_ACTIVATE_SUPER_A_TIER" in markdown


def test_report_says_no_probability_betting_staking_roi_changes(tmp_path):
    _df, markdown = register.run(tmp_path)

    assert "No probability logic changed" in markdown
    assert "No betting/staking/ROI logic changed" in markdown


def test_report_includes_accepted_phase11_3_defensive_rules(tmp_path):
    _df, markdown = register.run(tmp_path)

    assert "DOWNGRADE + low control -> HARD_NO_GO" in markdown
    assert "DOWNGRADE + medium_fav -> HARD_NO_GO" in markdown
    assert "DOWNGRADE + late season -> HARD_NO_GO" in markdown
    assert "HARD_NO_GO confirmations for low control and medium_fav" in markdown


def test_report_includes_rejected_ligue1_relaxations(tmp_path):
    _df, markdown = register.run(tmp_path)

    assert "No Ligue 1 source relaxation" in markdown
    assert "No relaxation for BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO" in markdown
    assert "No relaxation for SUPPRESSED_WITH_WARNING" in markdown
    assert "No relaxation for LEAGUE_PROFILE_SUPPRESSION" in markdown


def test_script_does_not_modify_market_tier_probability_or_recommended_logic(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    register.run(tmp_path)

    after = {path: _hash(path) for path in protected}
    assert after == before
