# -*- coding: utf-8 -*-
"""Tests for Phase-3 tier recalibration.

Covers:
  - A_TIER score threshold (>= 85)
  - Warning-flag downgrade (A_TIER + warning → B_TIER)
  - Ligue 1 A_TIER cap (→ B_TIER)
  - BOTH_OVER25_BTTS permanent HARD_NO_GO
  - Watchlist formatter (format_watchlist)
  - Watchlist file appender (append_watchlist_to_report)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.diagnostics.market_tier import build_market_tier
from football_prediction_v19.reports.watchlist import (
    format_watchlist,
    append_watchlist_to_report,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_phase3_rec(
    subtype: str = "UNDER_35",
    strength: str = "HIGH",
    warning: str = "",
    preferred: str = "UNDER_35",
    chaos: float = 3.0,
    league: str = "EPL",
    profile: str = "",
    confidence: str = "HIGH",
    data_warning: bool = False,
) -> dict:
    return {
        "recommended_market_type":    "UNDER",
        "recommended_market_subtype": subtype,
        "recommended_market_read":    "test_read",
        "league_adjusted_strength":   strength,
        "league":                     league,
        "league_profile":             profile,
        "confidence":                 confidence,
        "chaos_score_10":             chaos,
        "data_warning":               data_warning,
        "league_warning_flags":       warning,
        "league_preferred_subtype":   preferred,
        "league_suppressed_subtype":  "",
    }


def _make_watchlist_pred(
    tier: str,
    score: int,
    home: str = "HomeFC",
    away: str = "AwayFC",
    subtype: str = "UNDER_35",
    reason: str = "test reason",
) -> dict:
    return {
        "market_tier":               tier,
        "market_tier_score":         score,
        "market_tier_reason":        reason,
        "recommended_market_subtype": subtype,
        "home_team":                 home,
        "away_team":                 away,
    }


# ===========================================================================
# TestATierThreshold (4 tests)
# ===========================================================================

class TestATierThreshold:
    def test_score_84_is_b_tier(self):
        """HIGH + A_TIER subtype + no preferred subtype + neutral chaos → score 78 < 85 → B_TIER."""
        # score = 50 + 20 (HIGH) + 8 (A_TIER subtype) = 78; clamped to A_TIER [65,100] → 78 < 85 → B_TIER
        rec = _make_phase3_rec(subtype="UNDER_35", strength="HIGH", preferred="", chaos=5.0)
        result = build_market_tier(rec)
        assert result["market_tier"] == "B_TIER", (
            f"Score-78 case should be B_TIER, got {result['market_tier']} "
            f"(score={result['market_tier_score']})"
        )

    def test_score_85_or_above_is_a_tier(self):
        """HIGH + A_TIER subtype + preferred subtype + low chaos → score 93 >= 85 → A_TIER."""
        # score = 50 + 20 + 8 + 10 (preferred) + 5 (chaos<4) = 93
        rec = _make_phase3_rec(subtype="UNDER_35", strength="HIGH", preferred="UNDER_35", chaos=3.0)
        result = build_market_tier(rec)
        assert result["market_tier"] == "A_TIER", (
            f"Score-93 case should be A_TIER, got {result['market_tier']} "
            f"(score={result['market_tier_score']})"
        )

    def test_score_86_is_a_tier(self):
        """Any score >= 85 keeps A_TIER."""
        rec = _make_phase3_rec(subtype="UNDER_35", strength="HIGH", preferred="UNDER_35", chaos=3.5)
        result = build_market_tier(rec)
        assert result["market_tier"] == "A_TIER"
        assert result["market_tier_score"] >= 85

    def test_score_64_is_c_or_b_tier_not_a(self):
        """MEDIUM strength cannot qualify for A_TIER at all."""
        rec = _make_phase3_rec(subtype="UNDER_35", strength="MEDIUM", preferred="UNDER_35", chaos=3.0)
        result = build_market_tier(rec)
        assert result["market_tier"] != "A_TIER"


# ===========================================================================
# TestWarningFlagDowngrade (3 tests)
# ===========================================================================

class TestWarningFlagDowngrade:
    def test_a_tier_with_warning_flags_becomes_b_tier(self):
        """A_TIER + active warning flags → B_TIER with DOWNGRADED reason."""
        rec = _make_phase3_rec(
            subtype="UNDER_35",
            strength="HIGH",
            preferred="UNDER_35",
            chaos=3.0,
            warning="Some league warning",
            league="EPL",
        )
        result = build_market_tier(rec)
        assert result["market_tier"] == "B_TIER", (
            f"Expected B_TIER (warning downgrade), got {result['market_tier']}"
        )
        assert "[DOWNGRADED: warning_flags active]" in result["market_tier_reason"]

    def test_a_tier_without_warning_stays_a_tier(self):
        """A_TIER without warning flags stays A_TIER."""
        rec = _make_phase3_rec(
            subtype="UNDER_35",
            strength="HIGH",
            preferred="UNDER_35",
            chaos=3.0,
            warning="",
        )
        result = build_market_tier(rec)
        assert result["market_tier"] == "A_TIER"

    def test_b_tier_not_affected_by_warning_downgrade_rule(self):
        """Warning-flag downgrade rule only applies to A_TIER; B_TIER stays B_TIER."""
        rec = _make_phase3_rec(
            subtype="UNDER_35",
            strength="MEDIUM",
            preferred="UNDER_35",
            chaos=3.0,
            warning="Some warning",
        )
        result = build_market_tier(rec)
        # MEDIUM strength cannot reach A_TIER; result should be DOWNGRADE not B_TIER via A downgrade
        assert result["market_tier"] != "A_TIER"
        assert "[DOWNGRADED: warning_flags active]" not in result["market_tier_reason"]


# ===========================================================================
# TestLigue1Cap (3 tests)
# ===========================================================================

class TestLigue1Cap:
    def test_ligue1_a_tier_capped_to_b_tier(self):
        """Ligue 1 + A_TIER (score >= 85, no warning) → B_TIER with LIGUE1_CAP reason."""
        rec = _make_phase3_rec(
            subtype="UNDER_35",
            strength="HIGH",
            preferred="UNDER_35",
            chaos=3.0,
            league="Ligue 1",
            profile="ligue1_cautious",
            warning="",
        )
        result = build_market_tier(rec)
        assert result["market_tier"] == "B_TIER", (
            f"Ligue 1 A_TIER should be capped to B_TIER, got {result['market_tier']}"
        )
        assert "[LIGUE1_CAP: A_TIER→B_TIER]" in result["market_tier_reason"]

    def test_ligue1_b_tier_unchanged(self):
        """Ligue 1 B_TIER is not affected by the Ligue 1 cap."""
        rec = _make_phase3_rec(
            subtype="UNDER_35",
            strength="MEDIUM",
            preferred="",
            chaos=3.0,
            league="Ligue 1",
            profile="ligue1_cautious",
            warning="",
        )
        result = build_market_tier(rec)
        assert result["market_tier"] != "A_TIER"
        assert "[LIGUE1_CAP" not in result["market_tier_reason"]

    def test_non_ligue1_a_tier_unchanged(self):
        """Non-Ligue-1 A_TIER (score >= 85) is not capped."""
        rec = _make_phase3_rec(
            subtype="UNDER_35",
            strength="HIGH",
            preferred="UNDER_35",
            chaos=3.0,
            league="Bundesliga",
            profile="",
            warning="",
        )
        result = build_market_tier(rec)
        assert result["market_tier"] == "A_TIER"
        assert "[LIGUE1_CAP" not in result["market_tier_reason"]


# ===========================================================================
# TestBothOver25BttsHardNoGo (4 tests)
# ===========================================================================

class TestBothOver25BttsHardNoGo:
    def test_always_hard_no_go_regardless_of_score(self):
        """BOTH_OVER25_BTTS is always HARD_NO_GO, even with HIGH strength."""
        rec = _make_phase3_rec(
            subtype="BOTH_OVER25_BTTS",
            strength="HIGH",
            preferred="BOTH_OVER25_BTTS",
            chaos=1.0,
        )
        result = build_market_tier(rec)
        assert result["market_tier"] == "HARD_NO_GO"

    def test_always_hard_no_go_regardless_of_league(self):
        """BOTH_OVER25_BTTS is HARD_NO_GO in any league."""
        for league in ("EPL", "Bundesliga", "Eredivisie", "Premier League"):
            rec = _make_phase3_rec(subtype="BOTH_OVER25_BTTS", league=league)
            result = build_market_tier(rec)
            assert result["market_tier"] == "HARD_NO_GO", (
                f"Expected HARD_NO_GO for {league}, got {result['market_tier']}"
            )

    def test_reason_contains_historical_rate(self):
        """Reason must mention the 48.7% historical accuracy."""
        rec = _make_phase3_rec(subtype="BOTH_OVER25_BTTS")
        result = build_market_tier(rec)
        assert "48.7%" in result["market_tier_reason"]

    def test_subtype_suppressed_flag_present(self):
        """SUBTYPE_SUPPRESSED flag must appear in market_tier_flags."""
        rec = _make_phase3_rec(subtype="BOTH_OVER25_BTTS")
        result = build_market_tier(rec)
        assert "SUBTYPE_SUPPRESSED" in result["market_tier_flags"]


# ===========================================================================
# TestWatchlistFormatter (5 tests)
# ===========================================================================

class TestWatchlistFormatter:
    def test_empty_predictions_shows_keine_eintraege(self):
        """Empty list → both sections show [keine Einträge]."""
        output = format_watchlist([])
        assert "[keine Einträge]" in output
        assert output.count("[keine Einträge]") >= 2

    def test_priority_section_contains_a_and_b_tier(self):
        """A_TIER and B_TIER entries appear in PRIORITY WATCHLIST section."""
        preds = [
            _make_watchlist_pred("A_TIER", 90, home="Arsenal", away="Chelsea"),
            _make_watchlist_pred("B_TIER", 65, home="City", away="United"),
            _make_watchlist_pred("HARD_NO_GO", 10, home="X", away="Y"),
        ]
        output = format_watchlist(preds)
        priority_section = output.split("===")[2]  # text after "=== PRIORITY WATCHLIST ==="
        assert "Arsenal" in priority_section
        assert "City" in priority_section

    def test_nogo_section_contains_only_hard_no_go(self):
        """Only HARD_NO_GO entries appear in the NO-GO LISTE section."""
        preds = [
            _make_watchlist_pred("A_TIER", 90, home="Arsenal", away="Chelsea"),
            _make_watchlist_pred("HARD_NO_GO", 10, home="X", away="Y"),
        ]
        output = format_watchlist(preds)
        nogo_section = output.split("=== NO-GO LISTE ===")[1]
        assert "[NO-GO]" in nogo_section
        # A_TIER entry should NOT appear in NO-GO section
        assert "Arsenal" not in nogo_section

    def test_priority_sorted_score_desc(self):
        """Priority section is sorted by market_tier_score descending."""
        preds = [
            _make_watchlist_pred("B_TIER", 60, home="Low", away="Score"),
            _make_watchlist_pred("A_TIER", 95, home="High", away="Score"),
            _make_watchlist_pred("B_TIER", 70, home="Mid", away="Score"),
        ]
        output = format_watchlist(preds)
        priority_section = output.split("=== NO-GO LISTE ===")[0]
        high_pos = priority_section.index("High")
        mid_pos  = priority_section.index("Mid")
        low_pos  = priority_section.index("Low")
        assert high_pos < mid_pos < low_pos, "Not sorted by score DESC"

    def test_nogo_sorted_score_asc(self):
        """No-go section is sorted by market_tier_score ascending."""
        preds = [
            _make_watchlist_pred("HARD_NO_GO", 20, home="HighNG", away="X"),
            _make_watchlist_pred("HARD_NO_GO", 5,  home="LowNG",  away="Y"),
        ]
        output = format_watchlist(preds)
        nogo_section = output.split("=== NO-GO LISTE ===")[1]
        low_pos  = nogo_section.index("LowNG")
        high_pos = nogo_section.index("HighNG")
        assert low_pos < high_pos, "No-go section not sorted by score ASC"


# ===========================================================================
# TestAppendWatchlist (2 tests)
# ===========================================================================

class TestAppendWatchlist:
    def test_appends_to_existing_file(self):
        """append_watchlist_to_report appends to an existing file."""
        preds = [_make_watchlist_pred("A_TIER", 90)]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("EXISTING CONTENT\n")
            tmp_path = fh.name

        try:
            append_watchlist_to_report(tmp_path, preds)
            content = Path(tmp_path).read_text(encoding="utf-8")
            assert "EXISTING CONTENT" in content
            assert "PRIORITY WATCHLIST" in content
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_creates_file_if_not_exists(self):
        """append_watchlist_to_report creates file if it does not exist."""
        preds = [_make_watchlist_pred("B_TIER", 65)]
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = str(Path(tmpdir) / "new_report.txt")
            append_watchlist_to_report(report_path, preds)
            content = Path(report_path).read_text(encoding="utf-8")
            assert "PRIORITY WATCHLIST" in content
