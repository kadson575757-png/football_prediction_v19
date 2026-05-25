# -*- coding: utf-8 -*-
"""Tests for evaluator ensemble diagnostics summaries."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_daily_recommendations import _append_ensemble_analysis_section  # noqa: E402


def test_evaluator_warns_when_ensemble_fields_unavailable():
    lines: list[str] = []
    scored = pd.DataFrame({
        "type_success": [True, False],
        "subtype_success": [True, False],
    })

    _append_ensemble_analysis_section(lines, scored)

    text = "\n".join(lines)
    assert "WARNING: ensemble_agreement column is unavailable." in text


def test_evaluator_warns_when_ensemble_agreement_blank_for_all_rows():
    lines: list[str] = []
    scored = pd.DataFrame({
        "type_success": [True, False],
        "ensemble_agreement": ["", ""],
        "ensemble_note": ["", ""],
    })

    _append_ensemble_analysis_section(lines, scored)

    text = "\n".join(lines)
    assert "WARNING: ensemble_agreement is blank for all rows." in text


def test_evaluator_adds_success_rate_by_ensemble_agreement_when_present():
    lines: list[str] = []
    scored = pd.DataFrame({
        "type_success": [True, False, True],
        "ensemble_agreement": ["HIGH", "LOW", "NONE"],
        "ensemble_note": ["CONSENSUS", "DISAGREEMENT", "single"],
    })

    _append_ensemble_analysis_section(lines, scored)

    text = "\n".join(lines)
    assert "SUCCESS RATE BY ENSEMBLE AGREEMENT:" in text
    assert "HIGH" in text
    assert "LOW" in text
    assert "NONE" in text
