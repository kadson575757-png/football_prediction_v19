# -*- coding: utf-8 -*-
"""Tests for scripts/_watchlist.py — Priority Watchlist and No-Go List.

Tests cover:
- A_TIER and B_TIER rows appear on the watchlist
- HARD_NO_GO rows are excluded from watchlist
- La Liga BTTS / BOTH_OVER25_BTTS subtypes excluded from watchlist
- HARD_NO_GO rows appear in No-Go List
- SUPPRESSED+warning rows appear in No-Go List
- Sort order: market_tier_score DESC, then strength rank
- Empty results produce empty-state messages (no crash)
- print_priority_watchlist output contains expected section headings
- No betting/ROI language in output
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

# The scripts/ directory is not a package; add it to sys.path so _watchlist can be imported.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _watchlist import (
    _watchlist_rows,
    _nogo_rows,
    _is_la_liga,
    _tier_score,
    _strength_rank,
    print_priority_watchlist,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(
    home: str = "Home FC",
    away: str = "Away FC",
    tier: str = "A_TIER",
    score: int = 88,
    strength: str = "HIGH",
    subtype: str = "UNDER_35",
    warning: str = "",
) -> dict:
    """Build a minimal result row matching the structure used in daily scripts."""
    return {
        "home": home,
        "away": away,
        "recommended_market": {
            "market_tier":                tier,
            "market_tier_score":          score,
            "market_tier_reason":         "test reason",
            "market_tier_flags":          "",
            "league_adjusted_strength":   strength,
            "league_warning_flags":       warning,
            "recommended_market_subtype": subtype,
            "recommended_market_read":    "test_read",
            "recommended_market_type":    "UNDER",
        },
    }


def _capture(results: list[dict], league: str) -> str:
    """Capture print_priority_watchlist stdout output as a string."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        print_priority_watchlist(results, league)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


# ---------------------------------------------------------------------------
# _is_la_liga
# ---------------------------------------------------------------------------

class TestIsLaLiga:
    @pytest.mark.parametrize("league", ["La Liga", "la liga", "LA LIGA", "La Liga 2"])
    def test_la_liga_variants(self, league):
        assert _is_la_liga(league) is True

    @pytest.mark.parametrize("league", ["Serie A", "Eredivisie", "EPL", "Belgian Pro League", ""])
    def test_non_la_liga(self, league):
        assert _is_la_liga(league) is False


# ---------------------------------------------------------------------------
# _tier_score
# ---------------------------------------------------------------------------

class TestTierScore:
    def test_int_score(self):
        assert _tier_score({"market_tier_score": 88}) == 88

    def test_string_score(self):
        assert _tier_score({"market_tier_score": "70"}) == 70

    def test_missing_score(self):
        assert _tier_score({}) == 0

    def test_none_score(self):
        assert _tier_score({"market_tier_score": None}) == 0

    def test_invalid_score(self):
        assert _tier_score({"market_tier_score": "n/a"}) == 0


# ---------------------------------------------------------------------------
# _strength_rank
# ---------------------------------------------------------------------------

class TestStrengthRank:
    def test_high_is_best(self):
        assert _strength_rank({"league_adjusted_strength": "HIGH"}) == 0

    def test_medium(self):
        assert _strength_rank({"league_adjusted_strength": "MEDIUM"}) == 1

    def test_low(self):
        assert _strength_rank({"league_adjusted_strength": "LOW"}) == 2

    def test_suppressed_worst(self):
        assert _strength_rank({"league_adjusted_strength": "SUPPRESSED"}) == 3

    def test_missing_defaults_to_low(self):
        assert _strength_rank({}) == 2


# ---------------------------------------------------------------------------
# _watchlist_rows
# ---------------------------------------------------------------------------

class TestWatchlistRows:
    def test_a_tier_included(self):
        rows = _watchlist_rows([_row(tier="A_TIER")], "EPL")
        assert len(rows) == 1

    def test_b_tier_included(self):
        rows = _watchlist_rows([_row(tier="B_TIER", score=70)], "EPL")
        assert len(rows) == 1

    def test_hard_nogo_excluded(self):
        rows = _watchlist_rows([_row(tier="HARD_NO_GO", score=5)], "EPL")
        assert len(rows) == 0

    def test_c_tier_excluded(self):
        rows = _watchlist_rows([_row(tier="C_TIER", score=40)], "EPL")
        assert len(rows) == 0

    def test_downgrade_excluded(self):
        rows = _watchlist_rows([_row(tier="DOWNGRADE", score=30)], "EPL")
        assert len(rows) == 0

    def test_observe_only_excluded(self):
        rows = _watchlist_rows([_row(tier="OBSERVE_ONLY", score=10)], "EPL")
        assert len(rows) == 0

    # La Liga exclusions
    def test_la_liga_btts_excluded(self):
        rows = _watchlist_rows(
            [_row(tier="A_TIER", subtype="BTTS")], "La Liga"
        )
        assert len(rows) == 0

    def test_la_liga_both_over25_btts_excluded(self):
        rows = _watchlist_rows(
            [_row(tier="A_TIER", subtype="BOTH_OVER25_BTTS")], "La Liga"
        )
        assert len(rows) == 0

    def test_la_liga_under35_not_excluded(self):
        rows = _watchlist_rows(
            [_row(tier="A_TIER", subtype="UNDER_35")], "La Liga"
        )
        assert len(rows) == 1

    def test_eredivisie_btts_not_excluded(self):
        """BTTS exclusion is La Liga–specific only."""
        rows = _watchlist_rows(
            [_row(tier="B_TIER", subtype="BTTS")], "Eredivisie"
        )
        assert len(rows) == 1

    def test_sort_by_score_descending(self):
        results = [
            _row(home="Low", score=65, tier="B_TIER"),
            _row(home="High", score=88, tier="A_TIER"),
            _row(home="Mid", score=70, tier="B_TIER"),
        ]
        rows = _watchlist_rows(results, "EPL")
        assert rows[0]["home"] == "High"
        assert rows[1]["home"] == "Mid"
        assert rows[2]["home"] == "Low"

    def test_same_score_sorted_by_strength(self):
        results = [
            _row(home="Low", score=70, strength="LOW"),
            _row(home="High", score=70, strength="HIGH"),
            _row(home="Med", score=70, strength="MEDIUM"),
        ]
        rows = _watchlist_rows(results, "EPL")
        assert rows[0]["home"] == "High"
        assert rows[1]["home"] == "Med"
        assert rows[2]["home"] == "Low"

    def test_empty_results(self):
        assert _watchlist_rows([], "EPL") == []


# ---------------------------------------------------------------------------
# _nogo_rows
# ---------------------------------------------------------------------------

class TestNogoRows:
    def test_hard_nogo_included(self):
        rows = _nogo_rows([_row(tier="HARD_NO_GO", score=5)])
        assert len(rows) == 1

    def test_suppressed_with_warning_included(self):
        rows = _nogo_rows([_row(tier="C_TIER", strength="SUPPRESSED", warning="some warning")])
        assert len(rows) == 1

    def test_suppressed_without_warning_excluded(self):
        rows = _nogo_rows([_row(tier="C_TIER", strength="SUPPRESSED", warning="")])
        assert len(rows) == 0

    def test_a_tier_clean_excluded(self):
        rows = _nogo_rows([_row(tier="A_TIER", strength="HIGH", warning="")])
        assert len(rows) == 0

    def test_b_tier_with_warning_not_included_unless_suppressed(self):
        """B_TIER with a warning but not SUPPRESSED strength → not in No-Go."""
        rows = _nogo_rows([_row(tier="B_TIER", strength="MEDIUM", warning="some warning")])
        assert len(rows) == 0

    def test_empty_results(self):
        assert _nogo_rows([]) == []

    def test_multiple_hard_nogo(self):
        results = [
            _row(tier="HARD_NO_GO", home="A"),
            _row(tier="HARD_NO_GO", home="B"),
            _row(tier="A_TIER", home="C"),
        ]
        rows = _nogo_rows(results)
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# print_priority_watchlist output
# ---------------------------------------------------------------------------

class TestPrintPriorityWatchlist:
    def test_section_heading_watchlist(self):
        out = _capture([_row()], "EPL")
        assert "PRIORITY WATCHLIST" in out

    def test_section_heading_nogo(self):
        out = _capture([_row()], "EPL")
        assert "NO-GO LIST" in out

    def test_diagnostic_disclaimer_present(self):
        out = _capture([_row()], "EPL")
        assert "diagnostic only" in out.lower()

    def test_no_betting_language(self):
        out = _capture([_row()], "EPL")
        forbidden = ["bet ", "betting", "stake", "staking", "roi", "profit", "value bet"]
        lower_out = out.lower()
        for word in forbidden:
            assert word not in lower_out, f"Forbidden term found: {word!r}"

    def test_a_tier_row_appears_in_output(self):
        r = _row(home="Arsenal", away="Chelsea", tier="A_TIER", score=88)
        out = _capture([r], "EPL")
        assert "Arsenal" in out

    def test_hard_nogo_in_nogo_section(self):
        r = _row(home="BadMatch", away="Skip FC", tier="HARD_NO_GO", score=5)
        out = _capture([r], "EPL")
        assert "BadMatch" in out
        # Must be in the No-Go section, not the Watchlist section
        watchlist_section, nogo_section = out.split("NO-GO LIST", 1)
        assert "BadMatch" not in watchlist_section
        assert "BadMatch" in nogo_section

    def test_la_liga_btts_not_in_watchlist_section(self):
        r = _row(home="Sevilla", away="Barcelona", tier="A_TIER", subtype="BTTS")
        out = _capture([r], "La Liga")
        # Split at NO-GO LIST to isolate watchlist section
        watchlist_section = out.split("NO-GO LIST")[0]
        assert "Sevilla" not in watchlist_section

    def test_empty_watchlist_message(self):
        # All HARD_NO_GO → watchlist is empty
        r = _row(tier="HARD_NO_GO", score=5)
        out = _capture([r], "EPL")
        assert "No A_TIER or B_TIER" in out

    def test_empty_nogo_message(self):
        # All clean A_TIER → no-go is empty
        r = _row(tier="A_TIER", score=88, strength="HIGH", warning="")
        out = _capture([r], "EPL")
        assert "No HARD_NO_GO" in out

    def test_multiple_rows_sorted_in_output(self):
        results = [
            _row(home="Low", score=65, tier="B_TIER"),
            _row(home="High", score=88, tier="A_TIER"),
        ]
        out = _capture(results, "EPL")
        # "High" should appear before "Low" in the watchlist section
        watchlist_section = out.split("NO-GO LIST")[0]
        pos_high = watchlist_section.find("High")
        pos_low  = watchlist_section.find("Low")
        assert pos_high < pos_low

    def test_no_crash_on_empty_results(self):
        """Must not raise any exception for empty results."""
        _capture([], "EPL")

    def test_no_crash_on_missing_fields(self):
        """Must not raise even when recommended_market is mostly empty."""
        r = {"home": "X", "away": "Y", "recommended_market": {}}
        _capture([r], "EPL")

    def test_custom_sep_used(self):
        """Custom sep= argument must appear in output."""
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            print_priority_watchlist([_row()], "EPL", sep="***CUSTOM***")
        finally:
            sys.stdout = old
        assert "***CUSTOM***" in buf.getvalue()

    def test_all_scripts_import_watchlist(self):
        """All 7 daily scripts must import print_priority_watchlist."""
        scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
        daily_scripts = [
            "epl_daily_probability_report.py",
            "laliga_daily_probability_report.py",
            "d2_daily_probability_report.py",
            "eredivisie_daily_probability_report.py",
            "seriea_ligue1_daily_probability_report.py",
            "belgium_daily_probability_report.py",
            "brazil_daily_probability_report.py",
        ]
        for script_name in daily_scripts:
            text = (scripts_dir / script_name).read_text(encoding="utf-8")
            assert "from _watchlist import print_priority_watchlist" in text, (
                f"{script_name} is missing 'from _watchlist import print_priority_watchlist'"
            )
            assert "print_priority_watchlist(" in text, (
                f"{script_name} is missing a call to print_priority_watchlist()"
            )
