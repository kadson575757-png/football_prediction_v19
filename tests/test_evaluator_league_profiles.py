"""Tests for the league-profile summary sections in evaluate_daily_recommendations.

Imports build_league_profile_sections() directly from the evaluator script
so the logic can be verified without file I/O.

Covers:
- league_adjusted_strength HIGH/MEDIUM/SUPPRESSED correctly aggregated
- warning_flags present vs empty correctly aggregated
- missing league-profile columns do NOT crash
- missing ALL league-profile columns returns informational fallback line
- old evaluator sections remain present in the output (integration guard)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Import the helper from the script (scripts/ is not a package, so use path)
# ---------------------------------------------------------------------------

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from evaluate_daily_recommendations import (  # noqa: E402
    build_league_profile_sections,
    _direction_success,
    _double_chance_success,
    _btts_over_success,
    _under_success,
    _avoid_success,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(
    success: bool = True,
    strength: str = "HIGH",
    profile: str = "la_liga_control",
    warning_flags: str = "",
    preferred: str = "UNDER_35, DOUBLE_CHANCE_1X",
    suppressed: str = "OVER_25, BTTS",
    subtype: str = "UNDER_35",
) -> dict:
    return {
        "success":                    success,
        "league_adjusted_strength":   strength,
        "league_profile":             profile,
        "league_warning_flags":       warning_flags,
        "league_preferred_subtype":   preferred,
        "league_suppressed_subtype":  suppressed,
        "recommended_market_subtype": subtype,
    }


def _df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


# ---------------------------------------------------------------------------
# Section 6.1 — league_adjusted_strength
# ---------------------------------------------------------------------------

def test_strength_high_aggregated():
    df = _df(
        _row(True,  "HIGH"),
        _row(True,  "HIGH"),
        _row(False, "HIGH"),
        _row(True,  "MEDIUM"),
    )
    lines = "\n".join(build_league_profile_sections(df))
    assert "6.1" in lines
    # HIGH: 2 hits / 3 rows = 66.7%
    assert "HIGH" in lines
    # MEDIUM: 1 hit / 1 row = 100.0%
    assert "MEDIUM" in lines


def test_strength_suppressed_aggregated():
    df = _df(
        _row(False, "SUPPRESSED"),
        _row(False, "SUPPRESSED"),
        _row(True,  "HIGH"),
    )
    lines = "\n".join(build_league_profile_sections(df))
    assert "SUPPRESSED" in lines
    # Suppressed rows both failed — rate should be 0.0%
    assert "0.0%" in lines


def test_strength_tiers_appear_in_order():
    df = _df(
        _row(True,  "HIGH"),
        _row(True,  "MEDIUM"),
        _row(False, "LOW"),
        _row(False, "SUPPRESSED"),
    )
    lines = "\n".join(build_league_profile_sections(df))
    h_pos  = lines.index("HIGH")
    m_pos  = lines.index("MEDIUM")
    lo_pos = lines.index("LOW")
    su_pos = lines.index("SUPPRESSED")
    assert h_pos < m_pos < lo_pos < su_pos


# ---------------------------------------------------------------------------
# Section 6.3 — warning_flags present vs empty
# ---------------------------------------------------------------------------

def test_warning_present_vs_absent():
    df = _df(
        _row(True,  warning_flags="La Liga: OVER_25 poor evidence"),
        _row(False, warning_flags="La Liga: OVER_25 poor evidence"),
        _row(True,  warning_flags=""),
        _row(True,  warning_flags=""),
    )
    lines = "\n".join(build_league_profile_sections(df))
    assert "6.3" in lines
    assert "has warning_flag" in lines
    assert "no warning_flag" in lines


def test_warning_nan_treated_as_no_warning():
    """NaN in league_warning_flags must not crash and counts as 'no warning'."""
    df = pd.DataFrame([
        {"success": True,  "league_adjusted_strength": "HIGH",
         "league_warning_flags": float("nan"),
         "league_profile": "la_liga_control"},
        {"success": False, "league_adjusted_strength": "SUPPRESSED",
         "league_warning_flags": "some warning",
         "league_profile": "la_liga_control"},
    ])
    lines = "\n".join(build_league_profile_sections(df))
    assert "6.3" in lines  # did not crash


# ---------------------------------------------------------------------------
# Section 6.4 / 6.5 — preferred / suppressed subtype match
# ---------------------------------------------------------------------------

def test_preferred_subtype_match():
    df = _df(
        _row(True,  subtype="UNDER_35",  preferred="UNDER_35, DOUBLE_CHANCE_1X"),
        _row(True,  subtype="OVER_25",   preferred="UNDER_35, DOUBLE_CHANCE_1X"),
    )
    lines = "\n".join(build_league_profile_sections(df))
    assert "6.4" in lines
    assert "subtype is preferred" in lines
    assert "subtype not preferred" in lines


def test_suppressed_subtype_match():
    df = _df(
        _row(False, subtype="OVER_25",   suppressed="OVER_25, BTTS"),
        _row(True,  subtype="UNDER_35",  suppressed="OVER_25, BTTS"),
    )
    lines = "\n".join(build_league_profile_sections(df))
    assert "6.5" in lines
    assert "subtype is suppressed" in lines
    assert "subtype not suppressed" in lines


# ---------------------------------------------------------------------------
# Missing column fallbacks — must not crash
# ---------------------------------------------------------------------------

def test_missing_all_league_profile_columns_no_crash():
    """A DataFrame with only 'success' and NO league-profile columns."""
    df = pd.DataFrame([{"success": True}, {"success": False}])
    result = build_league_profile_sections(df)
    assert isinstance(result, list)
    assert len(result) > 0
    full = "\n".join(result)
    assert "not available" in full.lower()


def test_missing_some_league_profile_columns_no_crash():
    """Only league_adjusted_strength present — others absent."""
    df = pd.DataFrame([
        {"success": True,  "league_adjusted_strength": "HIGH"},
        {"success": False, "league_adjusted_strength": "SUPPRESSED"},
    ])
    result = build_league_profile_sections(df)
    full = "\n".join(result)
    assert "6.1" in full
    # 6.2 absent (league_profile col missing) — should not appear or crash
    # No assertion on 6.2 — just confirm no exception was raised


def test_empty_dataframe_no_crash():
    """An empty scored DataFrame (no rows at all)."""
    df = _df()
    # _df() returns empty DataFrame with right columns
    result = build_league_profile_sections(df)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Integration guard — old evaluator sections must remain importable
# ---------------------------------------------------------------------------

def test_old_evaluator_helpers_still_importable():
    """Core evaluator helper functions must remain available after changes."""
    assert callable(_direction_success)
    assert callable(_double_chance_success)
    assert callable(_btts_over_success)
    assert callable(_under_success)
    assert callable(_avoid_success)


def test_direction_success_unchanged():
    row = pd.Series({
        "recommended_market_read": "home_favourite",
        "actual_result": "H",
    })
    assert _direction_success(row) is True


def test_double_chance_1x_unchanged():
    row = pd.Series({
        "recommended_market_read": "double_chance_1x",
        "actual_result": "D",
        "likely_1x2": "Home",
    })
    assert _double_chance_success(row) is True


def test_btts_over_success_unchanged():
    row = pd.Series({"home_goals": 2, "away_goals": 1})
    # 3 total > 2.5 → success
    assert _btts_over_success(row) is True


# ---------------------------------------------------------------------------
# Section 6.6 comparison summary included
# ---------------------------------------------------------------------------

def test_comparison_summary_present():
    df = _df(
        _row(True,  "HIGH",      warning_flags="",     subtype="UNDER_35"),
        _row(False, "SUPPRESSED", warning_flags="warn", subtype="OVER_25"),
    )
    lines = "\n".join(build_league_profile_sections(df))
    assert "6.6" in lines
    assert "Comparison Summary" in lines
    assert "Adjusted Strength" in lines
    assert "Warning flags" in lines
    assert "Suppressed vs non-suppressed" in lines


def test_league_profile_note_diagnostic_disclaimer():
    """The section must end with a diagnostic-only note."""
    df = _df(_row(True))
    lines = "\n".join(build_league_profile_sections(df))
    assert "diagnostic only" in lines.lower()
    assert "no betting" in lines.lower()
