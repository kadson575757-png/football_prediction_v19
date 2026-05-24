# -*- coding: utf-8 -*-
"""Tests for MLS league profile and daily report support."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.diagnostics import (  # noqa: E402
    LEAGUE_PROFILES,
    apply_league_market_profile,
    build_market_tier,
)


def _load_mls_script():
    path = ROOT / "scripts" / "mls_daily_probability_report.py"
    spec = importlib.util.spec_from_file_location("mls_daily_probability_report", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _minimal_rec(subtype: str, mtype: str = "BTTS_OVER", strength: str = "STRONG") -> dict:
    return {
        "recommended_market_type": mtype,
        "recommended_market_subtype": subtype,
        "recommended_market_read": "test",
        "recommendation_strength": strength,
        "risk_note": "",
        "confidence": "HIGH",
        "data_warning": False,
        "chaos_score_10": 3.0,
    }


def test_mls_profile_exists():
    assert LEAGUE_PROFILES["MLS"]["profile_name"] == "mls_volatile"
    assert LEAGUE_PROFILES["Major League Soccer"]["profile_name"] == "mls_volatile"


def test_mls_profile_suppresses_btts():
    assert "BTTS" in LEAGUE_PROFILES["MLS"]["suppressed_subtypes"]
    result = apply_league_market_profile(_minimal_rec("BTTS"), "MLS")
    assert result["league_adjusted_strength"] == "SUPPRESSED"
    assert result["league_warning_flags"] != ""


def test_mls_profile_suppresses_both_over25_btts():
    assert "BOTH_OVER25_BTTS" in LEAGUE_PROFILES["MLS"]["suppressed_subtypes"]
    result = apply_league_market_profile(_minimal_rec("BOTH_OVER25_BTTS"), "MLS")
    assert result["league_adjusted_strength"] == "SUPPRESSED"
    assert result["league_warning_flags"] != ""


def test_mls_profile_prefers_double_chance_under_and_avoid():
    profile = LEAGUE_PROFILES["MLS"]
    assert "AVOID" in profile["preferred_types"]
    assert "DOUBLE_CHANCE_1X" in profile["preferred_subtypes"]
    assert "DOUBLE_CHANCE_X2" in profile["preferred_subtypes"]
    assert "UNDER_35" in profile["preferred_subtypes"]


@pytest.mark.parametrize(
    ("subtype", "mtype"),
    [
        ("DOUBLE_CHANCE_1X", "DOUBLE_CHANCE"),
        ("DOUBLE_CHANCE_X2", "DOUBLE_CHANCE"),
        ("UNDER_35", "UNDER"),
    ],
)
def test_mls_preferred_subtypes_promote_strength(subtype, mtype):
    result = apply_league_market_profile(_minimal_rec(subtype, mtype=mtype), "MLS")
    assert result["league_adjusted_strength"] == "HIGH"


def test_mls_daily_probability_report_preserves_market_tier_fields():
    rec = apply_league_market_profile(_minimal_rec("UNDER_35", mtype="UNDER"), "MLS")
    rec = build_market_tier(rec)
    row = {
        "recommended_market_type": rec["recommended_market_type"],
        "recommended_market_subtype": rec["recommended_market_subtype"],
        "league_adjusted_strength": rec["league_adjusted_strength"],
        "league_warning_flags": rec["league_warning_flags"],
        "market_tier": rec["market_tier"],
        "market_tier_score": rec["market_tier_score"],
        "market_tier_reason": rec["market_tier_reason"],
        "market_tier_flags": rec["market_tier_flags"],
    }
    for field in (
        "recommended_market_type",
        "recommended_market_subtype",
        "league_adjusted_strength",
        "league_warning_flags",
        "market_tier",
        "market_tier_score",
        "market_tier_reason",
        "market_tier_flags",
    ):
        assert field in row


def test_missing_historical_file_gives_clear_error(tmp_path, monkeypatch):
    module = _load_mls_script()
    monkeypatch.setattr(module, "HIST_RAW_2025", tmp_path / "missing_2025.csv")
    monkeypatch.setattr(module, "HIST_RAW_2026", tmp_path / "missing_2026.csv")
    monkeypatch.setattr(module, "HIST_PROCESSED", tmp_path / "missing_clean.csv")

    with pytest.raises(FileNotFoundError) as exc:
        module.load_history()

    assert str(exc.value) == module.MISSING_HISTORY_ERROR
