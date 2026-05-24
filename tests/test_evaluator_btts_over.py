# -*- coding: utf-8 -*-
"""Tests for BTTS_OVER success logic in evaluate_daily_recommendations.py.

Key invariant: BTTS_OVER success = actual_over2.5 OR actual_btts.
Either condition alone is sufficient; both false is the only miss.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Make the scripts directory importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_daily_recommendations import _btts_over_success  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: build a minimal row with just the goal columns the function needs
# ---------------------------------------------------------------------------

def _row(home: float | None, away: float | None) -> pd.Series:
    return pd.Series({"home_goals": home, "away_goals": away})


# ---------------------------------------------------------------------------
# 1. OR logic — task-mandated cases
# ---------------------------------------------------------------------------

def test_btts_over_succeeds_when_over25_true_and_btts_false():
    """3-0: total=3 (>2.5) but only home scored → over25 True, btts False → success."""
    result = _btts_over_success(_row(3, 0))
    assert result is True, f"Expected True (over25 hit), got {result!r}"


def test_btts_over_succeeds_when_btts_true_and_over25_false():
    """1-1: total=2 (not >2.5) but both teams scored → over25 False, btts True → success."""
    result = _btts_over_success(_row(1, 1))
    assert result is True, f"Expected True (btts hit), got {result!r}"


def test_btts_over_fails_when_both_false():
    """0-0: total=0, neither scored → over25 False, btts False → failure."""
    result = _btts_over_success(_row(0, 0))
    assert result is False, f"Expected False (both conditions miss), got {result!r}"


# ---------------------------------------------------------------------------
# 2. OR logic — additional boundary cases
# ---------------------------------------------------------------------------

def test_btts_over_succeeds_when_both_true():
    """2-1: total=3 (>2.5) AND both scored → both True → success."""
    result = _btts_over_success(_row(2, 1))
    assert result is True


def test_btts_over_succeeds_exact_boundary_3_goals_home_only():
    """3-0: exactly 3 goals (>2.5). btts=False. OR should still be True."""
    result = _btts_over_success(_row(3, 0))
    assert result is True


def test_btts_over_fails_exactly_2_goals_home_only():
    """2-0: total=2 (not >2.5), only home scored → both False → failure."""
    result = _btts_over_success(_row(2, 0))
    assert result is False


def test_btts_over_fails_exactly_2_goals_away_only():
    """0-2: total=2 (not >2.5), only away scored → both False → failure."""
    result = _btts_over_success(_row(0, 2))
    assert result is False


def test_btts_over_no_score_returns_none():
    """Missing score → function returns None (not evaluatable)."""
    result = _btts_over_success(_row(None, None))
    assert result is None


def test_btts_over_partial_score_home_missing_returns_none():
    result = _btts_over_success(_row(None, 2))
    assert result is None


def test_btts_over_partial_score_away_missing_returns_none():
    result = _btts_over_success(_row(1, None))
    assert result is None


# ---------------------------------------------------------------------------
# 3. Consistency: success column must always equal (over25 OR btts)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hg,ag,expected_over25,expected_btts,expected_or", [
    (0, 0, False, False, False),
    (1, 0, False, False, False),
    (0, 1, False, False, False),
    (1, 1, False, True,  True),
    (2, 0, False, False, False),
    (0, 2, False, False, False),
    (2, 1, True,  True,  True),
    (3, 0, True,  False, True),
    (0, 3, True,  False, True),
    (1, 2, True,  True,  True),
    (4, 0, True,  False, True),
    (2, 2, True,  True,  True),
    (3, 3, True,  True,  True),
])
def test_btts_over_or_equals_individual_signals(
    hg, ag, expected_over25, expected_btts, expected_or
):
    """For every goal combination: success == (over25 OR btts), always."""
    over25 = (hg + ag) > 2.5
    btts   = (hg > 0) and (ag > 0)
    assert over25 == expected_over25, f"{hg}-{ag}: over25 mismatch"
    assert btts   == expected_btts,   f"{hg}-{ag}: btts mismatch"
    assert (over25 or btts) == expected_or, f"{hg}-{ag}: OR mismatch"

    result = _btts_over_success(_row(hg, ag))
    assert result == expected_or, (
        f"_btts_over_success({hg}-{ag}): expected {expected_or!r}, got {result!r}. "
        f"over25={over25}, btts={btts}"
    )


# ---------------------------------------------------------------------------
# 4. Over25-only hit (3-0) should NOT count as BTTS, and vice versa
# ---------------------------------------------------------------------------

def test_3_0_is_over25_hit_not_btts():
    """3-0 scores over2.5 but BTTS is false. Success via over25 only."""
    hg, ag = 3, 0
    over25 = (hg + ag) > 2.5
    btts   = (hg > 0) and (ag > 0)
    assert over25 is True
    assert btts   is False
    assert _btts_over_success(_row(hg, ag)) is True  # OR → True


def test_1_1_is_btts_hit_not_over25():
    """1-1 satisfies BTTS but not Over2.5. Success via btts only."""
    hg, ag = 1, 1
    over25 = (hg + ag) > 2.5
    btts   = (hg > 0) and (ag > 0)
    assert over25 is False
    assert btts   is True
    assert _btts_over_success(_row(hg, ag)) is True  # OR → True
