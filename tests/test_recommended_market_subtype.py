# -*- coding: utf-8 -*-
"""Tests for recommended_market_subtype assignment and subtype success evaluation.

Covers:
- BTTS_OVER subtype resolution (OVER_25 / BTTS / BOTH_OVER25_BTTS)
- UNDER subtype resolution (UNDER_25 / UNDER_35)
- DIRECTION subtype resolution (DIRECTION_HOME / DIRECTION_AWAY)
- DOUBLE_CHANCE subtype resolution (DOUBLE_CHANCE_1X / DOUBLE_CHANCE_X2)
- AVOID subtype resolution (AVOID_VOLATILE / AVOID_LOW_CONTROL)
- OBSERVE_ONLY subtype resolution (OBSERVE_DATA_WARNING / NONE)
- Subtype success logic in evaluator
- No old fields removed
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_prediction_v19.diagnostics import ALLOWED_SUBTYPES, build_recommended_market
from football_prediction_v19.diagnostics.recommended_market import (
    ALLOWED_TYPES,
    _btts_over_subtype,
    _compute_subtype,
    _is_strong_btts,
    _is_strong_over25,
    _under_subtype,
)
from evaluate_daily_recommendations import _subtype_success  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_row(**kwargs) -> dict:
    """Minimal valid input row for build_recommended_market."""
    defaults = {
        "league": "EPL",
        "likely_1x2": "Home",
        "confidence": "MEDIUM",
        "control_score_10": 4.0,
        "chaos_score_10": 3.0,
        "model_home_prob": 0.50,
        "model_draw_prob": 0.25,
        "model_away_prob": 0.25,
        "over25_signal": "unclear",
        "btts_signal": "unclear",
        "goals": "",
        "probability_profile": "",
        "both_over": False,
        "both_btts": False,
        "data_warning": False,
    }
    defaults.update(kwargs)
    return defaults


def _eval_row(subtype: str, home_goals: float | None, away_goals: float | None) -> pd.Series:
    return pd.Series({
        "recommended_market_subtype": subtype,
        "home_goals": home_goals,
        "away_goals": away_goals,
    })


# ---------------------------------------------------------------------------
# 1. build_recommended_market always returns recommended_market_subtype
# ---------------------------------------------------------------------------

def test_subtype_always_present():
    rec = build_recommended_market(_base_row())
    assert "recommended_market_subtype" in rec, "recommended_market_subtype must be in returned dict"


def test_subtype_is_valid_value():
    for likely in ("Home", "Away", "Draw"):
        for conf in ("HIGH", "MEDIUM", "LOW", "NO-CONFIDENCE"):
            rec = build_recommended_market(_base_row(likely_1x2=likely, confidence=conf))
            assert rec["recommended_market_subtype"] in ALLOWED_SUBTYPES, (
                f"Invalid subtype: {rec['recommended_market_subtype']!r}"
            )


# ---------------------------------------------------------------------------
# 2. No old fields removed
# ---------------------------------------------------------------------------

_REQUIRED_OLD_FIELDS = {
    "recommended_market_type",
    "recommended_market_read",
    "recommendation_strength",
    "risk_note",
    "avoid_reason",
    "preferred_score_family",
    "diagnostic_only",
}


def test_all_old_fields_still_present():
    rec = build_recommended_market(_base_row())
    for field in _REQUIRED_OLD_FIELDS:
        assert field in rec, f"Old field missing: {field!r}"


def test_recommended_market_type_unchanged_values():
    """The type field still only emits the original six values."""
    for _ in range(3):  # a few inputs
        rec = build_recommended_market(_base_row())
        assert rec["recommended_market_type"] in ALLOWED_TYPES


# ---------------------------------------------------------------------------
# 3. BTTS_OVER subtype resolution — the three mandated cases
# ---------------------------------------------------------------------------

def test_btts_over_strong_over_only_gives_over25_subtype():
    """Strong over25 signal, no btts signal → subtype OVER_25."""
    row = _base_row(
        over25_signal="OVER likely",
        btts_signal="unclear",
        both_over=False,
        both_btts=False,
        chaos_score_10=4.0,
        league="Eredivisie",
    )
    result = _btts_over_subtype(row)
    assert result == "OVER_25", f"Expected OVER_25, got {result!r}"


def test_btts_over_strong_btts_only_gives_btts_subtype():
    """Strong btts signal, no over25 signal → subtype BTTS."""
    row = _base_row(
        over25_signal="unclear",
        btts_signal="BTTS YES likely",
        both_over=False,
        both_btts=False,
        chaos_score_10=4.0,
        league="Eredivisie",
    )
    result = _btts_over_subtype(row)
    assert result == "BTTS", f"Expected BTTS, got {result!r}"


def test_btts_over_both_strong_gives_both_over25_btts_subtype():
    """Both over25 and btts signals strong → subtype BOTH_OVER25_BTTS."""
    row = _base_row(
        over25_signal="OVER likely",
        btts_signal="BTTS YES likely",
        both_over=False,
        both_btts=False,
        chaos_score_10=4.0,
        league="Eredivisie",
    )
    result = _btts_over_subtype(row)
    assert result == "BOTH_OVER25_BTTS", f"Expected BOTH_OVER25_BTTS, got {result!r}"


def test_btts_over_both_flags_true_gives_both_subtype():
    """both_over=True and both_btts=True → BOTH_OVER25_BTTS."""
    row = _base_row(both_over=True, both_btts=True)
    assert _btts_over_subtype(row) == "BOTH_OVER25_BTTS"


def test_btts_over_only_both_over_flag_gives_over25():
    """both_over=True, no btts signal → OVER_25."""
    row = _base_row(both_over=True, both_btts=False, btts_signal="unclear")
    assert _btts_over_subtype(row) == "OVER_25"


def test_btts_over_only_both_btts_flag_gives_btts():
    """both_btts=True, no over25 signal → BTTS."""
    row = _base_row(both_btts=True, both_over=False, over25_signal="unclear")
    assert _btts_over_subtype(row) == "BTTS"


def test_btts_over_no_signals_defaults_to_over25():
    """No clear signal for either → default OVER_25 (not BTTS)."""
    row = _base_row(over25_signal="unclear", btts_signal="unclear")
    assert _btts_over_subtype(row) == "OVER_25"


# ---------------------------------------------------------------------------
# 4. BTTS_OVER via build_recommended_market — subtype propagates
# ---------------------------------------------------------------------------

def test_build_btts_over_with_strong_over_produces_over25_subtype():
    rec = build_recommended_market(_base_row(
        league="Eredivisie",
        over25_signal="OVER likely",
        btts_signal="unclear",
        chaos_score_10=4.0,
    ))
    assert rec["recommended_market_type"] == "BTTS_OVER"
    assert rec["recommended_market_subtype"] == "OVER_25"


def test_build_btts_over_with_strong_btts_produces_btts_subtype():
    rec = build_recommended_market(_base_row(
        league="Eredivisie",
        over25_signal="unclear",
        btts_signal="BTTS YES likely",
        chaos_score_10=4.0,
    ))
    assert rec["recommended_market_type"] == "BTTS_OVER"
    assert rec["recommended_market_subtype"] == "BTTS"


def test_build_btts_over_with_both_strong_produces_both_subtype():
    rec = build_recommended_market(_base_row(
        league="Eredivisie",
        over25_signal="OVER likely",
        btts_signal="BTTS YES likely",
        chaos_score_10=4.0,
    ))
    assert rec["recommended_market_type"] == "BTTS_OVER"
    assert rec["recommended_market_subtype"] == "BOTH_OVER25_BTTS"


# ---------------------------------------------------------------------------
# 5. UNDER subtype resolution
# ---------------------------------------------------------------------------

def test_under_25_when_under25_signal_and_low_chaos():
    row = _base_row(under25_signal="UNDER likely", chaos_score_10=2.5)
    assert _under_subtype(row, chaos=2.5) == "UNDER_25"


def test_under_35_when_under25_signal_but_chaos_too_high():
    row = _base_row(under25_signal="UNDER likely", chaos_score_10=4.0)
    assert _under_subtype(row, chaos=4.0) == "UNDER_35"


def test_under_35_when_no_strong_under25_signal():
    row = _base_row(under25_signal="unclear", chaos_score_10=2.0)
    assert _under_subtype(row, chaos=2.0) == "UNDER_35"


def test_under_25_boundary_chaos_exactly_3():
    row = _base_row(under25_signal="UNDER likely")
    assert _under_subtype(row, chaos=3.0) == "UNDER_25"


def test_under_35_boundary_chaos_just_above_3():
    row = _base_row(under25_signal="UNDER likely")
    assert _under_subtype(row, chaos=3.1) == "UNDER_35"


# ---------------------------------------------------------------------------
# 6. DIRECTION and DOUBLE_CHANCE subtypes via _compute_subtype
# ---------------------------------------------------------------------------

def _cs(rec_type, likely="Home", read="home_or_draw_1x", avoid_reason="",
         data_warning=False, chaos=3.0, row=None):
    return _compute_subtype(
        rec_type=rec_type, row=row or {}, likely=likely, read=read,
        avoid_reason=avoid_reason, data_warning=data_warning, chaos=chaos,
    )


def test_direction_home_subtype():
    assert _cs("DIRECTION", likely="Home") == "DIRECTION_HOME"


def test_direction_away_subtype():
    assert _cs("DIRECTION", likely="Away") == "DIRECTION_AWAY"


def test_direction_draw_gives_none():
    assert _cs("DIRECTION", likely="Draw") == "NONE"


def test_double_chance_1x_subtype():
    assert _cs("DOUBLE_CHANCE", read="home_or_draw_1X") == "DOUBLE_CHANCE_1X"


def test_double_chance_x2_subtype():
    assert _cs("DOUBLE_CHANCE", read="away_or_draw_X2") == "DOUBLE_CHANCE_X2"


def test_avoid_low_control_subtype():
    result = _cs("AVOID", avoid_reason="control below 1.5 and no strong goals signal")
    assert result == "AVOID_LOW_CONTROL"


def test_avoid_volatile_when_disagree_in_reason():
    result = _cs("AVOID", avoid_reason="model and market disagree while control is low")
    assert result == "AVOID_VOLATILE"


def test_avoid_volatile_when_confidence_in_reason():
    result = _cs("AVOID", avoid_reason="NO-CONFIDENCE 1X2 read")
    assert result == "AVOID_VOLATILE"


def test_observe_data_warning_subtype():
    assert _cs("OBSERVE_ONLY", data_warning=True) == "OBSERVE_DATA_WARNING"


def test_observe_none_when_no_data_warning():
    assert _cs("OBSERVE_ONLY", data_warning=False) == "NONE"


# ---------------------------------------------------------------------------
# 7. Subtype success in evaluator — per-subtype logic
# ---------------------------------------------------------------------------

def test_over25_subtype_success_on_3_goals():
    assert _subtype_success(_eval_row("OVER_25", 2, 1)) is True


def test_over25_subtype_success_on_3_0():
    """3-0: over25 True even though btts is False."""
    assert _subtype_success(_eval_row("OVER_25", 3, 0)) is True


def test_over25_subtype_fails_on_2_goals():
    assert _subtype_success(_eval_row("OVER_25", 1, 1)) is False


def test_btts_subtype_success_on_1_1():
    """1-1: btts True even though over25 is False."""
    assert _subtype_success(_eval_row("BTTS", 1, 1)) is True


def test_btts_subtype_fails_on_3_0():
    """3-0: over25 True but btts False → subtype BTTS should FAIL."""
    assert _subtype_success(_eval_row("BTTS", 3, 0)) is False


def test_btts_subtype_fails_on_0_0():
    assert _subtype_success(_eval_row("BTTS", 0, 0)) is False


def test_both_over25_btts_success_on_2_1():
    """2-1: both over25 True and btts True → BOTH_OVER25_BTTS success."""
    assert _subtype_success(_eval_row("BOTH_OVER25_BTTS", 2, 1)) is True


def test_both_over25_btts_fails_on_3_0():
    """3-0: over25 True but btts False → BOTH_OVER25_BTTS fails (AND logic)."""
    assert _subtype_success(_eval_row("BOTH_OVER25_BTTS", 3, 0)) is False


def test_both_over25_btts_fails_on_1_1():
    """1-1: btts True but over25 False → BOTH_OVER25_BTTS fails (AND logic)."""
    assert _subtype_success(_eval_row("BOTH_OVER25_BTTS", 1, 1)) is False


def test_both_over25_btts_fails_on_0_0():
    assert _subtype_success(_eval_row("BOTH_OVER25_BTTS", 0, 0)) is False


def test_under25_subtype_success_on_0_0():
    assert _subtype_success(_eval_row("UNDER_25", 0, 0)) is True


def test_under25_subtype_success_on_1_1():
    """1-1: total=2 < 2.5 → UNDER_25 success."""
    assert _subtype_success(_eval_row("UNDER_25", 1, 1)) is True


def test_under25_subtype_fails_on_2_1():
    """2-1: total=3 > 2.5 → UNDER_25 fails."""
    assert _subtype_success(_eval_row("UNDER_25", 2, 1)) is False


def test_under35_subtype_success_on_2_1():
    """2-1: total=3 < 3.5 → UNDER_35 success."""
    assert _subtype_success(_eval_row("UNDER_35", 2, 1)) is True


def test_under35_subtype_fails_on_2_2():
    """2-2: total=4 > 3.5 → UNDER_35 fails."""
    assert _subtype_success(_eval_row("UNDER_35", 2, 2)) is False


def test_double_chance_1x_success_on_home_win():
    assert _subtype_success(_eval_row("DOUBLE_CHANCE_1X", 2, 0)) is True


def test_double_chance_1x_success_on_draw():
    assert _subtype_success(_eval_row("DOUBLE_CHANCE_1X", 1, 1)) is True


def test_double_chance_1x_fails_on_away_win():
    assert _subtype_success(_eval_row("DOUBLE_CHANCE_1X", 0, 1)) is False


def test_double_chance_x2_success_on_away_win():
    assert _subtype_success(_eval_row("DOUBLE_CHANCE_X2", 0, 2)) is True


def test_double_chance_x2_success_on_draw():
    assert _subtype_success(_eval_row("DOUBLE_CHANCE_X2", 0, 0)) is True


def test_double_chance_x2_fails_on_home_win():
    assert _subtype_success(_eval_row("DOUBLE_CHANCE_X2", 2, 0)) is False


def test_avoid_volatile_returns_none():
    assert _subtype_success(_eval_row("AVOID_VOLATILE", 1, 0)) is None


def test_avoid_low_control_returns_none():
    assert _subtype_success(_eval_row("AVOID_LOW_CONTROL", 0, 0)) is None


def test_observe_data_warning_returns_none():
    assert _subtype_success(_eval_row("OBSERVE_DATA_WARNING", 2, 1)) is None


def test_none_subtype_returns_none():
    assert _subtype_success(_eval_row("NONE", 3, 0)) is None


def test_missing_goals_returns_none():
    assert _subtype_success(_eval_row("OVER_25", None, None)) is None


# ---------------------------------------------------------------------------
# 8. OVER_25 and BTTS are truly independent signals
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hg,ag,over25_expected,btts_expected", [
    (3, 0, True,  False),   # over25 only
    (1, 1, False, True),    # btts only
    (2, 1, True,  True),    # both
    (0, 0, False, False),   # neither
    (1, 0, False, False),   # neither
    (0, 3, True,  False),   # over25 only
])
def test_over25_and_btts_subtypes_are_independent(hg, ag, over25_expected, btts_expected):
    over25_result = _subtype_success(_eval_row("OVER_25", hg, ag))
    btts_result   = _subtype_success(_eval_row("BTTS",    hg, ag))
    assert over25_result == over25_expected, f"{hg}-{ag}: OVER_25 expected {over25_expected}"
    assert btts_result   == btts_expected,   f"{hg}-{ag}: BTTS expected {btts_expected}"


# ---------------------------------------------------------------------------
# 9. _is_strong_over25 / _is_strong_btts helpers
# ---------------------------------------------------------------------------

def test_strong_over25_with_both_over_flag():
    assert _is_strong_over25({"both_over": True}) is True


def test_strong_over25_with_signal_text():
    assert _is_strong_over25({"over25_signal": "OVER likely", "both_over": False}) is True


def test_not_strong_over25_when_unclear():
    assert _is_strong_over25({"over25_signal": "unclear", "both_over": False}) is False


def test_not_strong_over25_when_text_says_not():
    assert _is_strong_over25({"over25_signal": "not over", "both_over": False}) is False


def test_strong_btts_with_both_btts_flag():
    assert _is_strong_btts({"both_btts": True}) is True


def test_strong_btts_with_signal_text():
    assert _is_strong_btts({"btts_signal": "BTTS YES likely", "both_btts": False}) is True


def test_not_strong_btts_when_btts_no():
    assert _is_strong_btts({"btts_signal": "BTTS NO likely", "both_btts": False}) is False


def test_not_strong_btts_when_unclear():
    assert _is_strong_btts({"btts_signal": "unclear", "both_btts": False}) is False
