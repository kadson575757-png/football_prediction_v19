# -*- coding: utf-8 -*-
"""Tests for Belgian Pro League (B1) and Brasileiro Serie A (BRA) league support.

Covers:
- League code mappings in run_season_replay_audit
- Historical data file discovery
- League profile definitions (preferred/suppressed subtypes)
- market_tier field presence in daily report CSV output
- BOTH_OVER25_BTTS suppressed in both profiles
- BTTS suppressed in Brazil profile
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Import league code mapping from the replay audit script
sys.path.insert(0, str(ROOT / "scripts"))
import run_season_replay_audit as _replay

from football_prediction_v19.diagnostics import apply_league_market_profile, LEAGUE_PROFILES
from football_prediction_v19.diagnostics import build_market_tier, build_recommended_market


def _minimal_rec(subtype: str, mtype: str = "BTTS_OVER", strength: str = "STRONG") -> dict:
    """Build a minimal recommendation dict for profile/tier tests."""
    return {
        "recommended_market_type":    mtype,
        "recommended_market_subtype": subtype,
        "recommended_market_read":    "test",
        "recommendation_strength":    strength,
        "risk_note":                  "",
        "confidence":                 "HIGH",
        "data_warning":               False,
        "chaos_score_10":             3.0,
    }


# ---------------------------------------------------------------------------
# League code mapping
# ---------------------------------------------------------------------------

class TestLeagueCodeMapping:
    @pytest.mark.parametrize("name", [
        "Belgium",
        "Belgian Pro League",
        "Jupiler Pro League",
        "B1",
    ])
    def test_belgium_maps_to_b1(self, name):
        assert _replay.LEAGUE_TO_CODE[name] == "B1", (
            f"Expected '{name}' → 'B1', got '{_replay.LEAGUE_TO_CODE.get(name)}'"
        )

    @pytest.mark.parametrize("name", [
        "Brazil",
        "Brasileiro",
        "Brasileiro Serie A",
        "Campeonato Brasileiro Serie A",
        "BRA",
    ])
    def test_brazil_maps_to_bra(self, name):
        assert _replay.LEAGUE_TO_CODE[name] == "BRA", (
            f"Expected '{name}' → 'BRA', got '{_replay.LEAGUE_TO_CODE.get(name)}'"
        )

    def test_b1_reverse_mapping(self):
        assert _replay.CODE_TO_LEAGUE.get("B1") == "Belgian Pro League"

    def test_bra_reverse_mapping(self):
        assert _replay.CODE_TO_LEAGUE.get("BRA") == "Brasileiro Serie A"


# ---------------------------------------------------------------------------
# Historical data file discovery
# ---------------------------------------------------------------------------

class TestHistoricalDataFiles:
    def test_belgium_2024_raw_file_exists(self):
        p = ROOT / "data" / "raw" / "football_data_B1_2024.csv"
        assert p.exists(), f"Missing: {p}"

    def test_belgium_2025_raw_file_exists(self):
        p = ROOT / "data" / "raw" / "football_data_B1_2025.csv"
        assert p.exists(), f"Missing: {p}"

    def test_brazil_2024_raw_file_exists(self):
        p = ROOT / "data" / "raw" / "football_data_BRA_2024.csv"
        assert p.exists(), f"Missing: {p}"

    def test_brazil_2025_raw_file_exists(self):
        p = ROOT / "data" / "raw" / "football_data_BRA_2025.csv"
        assert p.exists(), f"Missing: {p}"

    def test_belgium_fixture_file_exists(self):
        p = ROOT / "data" / "upcoming_belgium_fixtures.csv"
        assert p.exists(), f"Missing: {p}"

    def test_brazil_fixture_file_exists(self):
        p = ROOT / "data" / "upcoming_brazil_fixtures.csv"
        assert p.exists(), f"Missing: {p}"

    def test_replay_audit_resolves_b1_2024(self):
        """replay audit _find_data_file logic: should find football_data_B1_2024.csv"""
        raw_dir = ROOT / "data" / "raw"
        candidate = raw_dir / "football_data_B1_2024.csv"
        assert candidate.exists(), (
            f"run_season_replay_audit would fail to find: {candidate}"
        )

    def test_replay_audit_resolves_bra_2024(self):
        raw_dir = ROOT / "data" / "raw"
        candidate = raw_dir / "football_data_BRA_2024.csv"
        assert candidate.exists(), (
            f"run_season_replay_audit would fail to find: {candidate}"
        )


# ---------------------------------------------------------------------------
# League profile definitions
# ---------------------------------------------------------------------------

class TestLeagueProfileDefinitions:
    @pytest.mark.parametrize("league_name", [
        "Belgium",
        "Belgian Pro League",
        "Jupiler Pro League",
    ])
    def test_belgium_profile_exists(self, league_name):
        assert league_name in LEAGUE_PROFILES, (
            f"LEAGUE_PROFILES missing entry for '{league_name}'"
        )

    @pytest.mark.parametrize("league_name", [
        "Brazil",
        "Brasileiro",
        "Brasileiro Serie A",
        "Campeonato Brasileiro Serie A",
    ])
    def test_brazil_profile_exists(self, league_name):
        assert league_name in LEAGUE_PROFILES, (
            f"LEAGUE_PROFILES missing entry for '{league_name}'"
        )

    def test_belgium_profile_id(self):
        assert LEAGUE_PROFILES["Belgian Pro League"]["profile_name"] == "belgium_balanced_goals"

    def test_brazil_profile_id(self):
        assert LEAGUE_PROFILES["Brasileiro Serie A"]["profile_name"] == "brazil_volatile_control"

    def test_belgium_preferred_subtypes_contain_under35(self):
        pref = LEAGUE_PROFILES["Belgian Pro League"]["preferred_subtypes"]
        assert "UNDER_35" in pref

    def test_belgium_preferred_subtypes_contain_double_chance(self):
        pref = LEAGUE_PROFILES["Belgian Pro League"]["preferred_subtypes"]
        assert "DOUBLE_CHANCE_1X" in pref
        assert "DOUBLE_CHANCE_X2" in pref

    def test_brazil_preferred_subtypes_contain_double_chance(self):
        pref = LEAGUE_PROFILES["Brasileiro Serie A"]["preferred_subtypes"]
        assert "DOUBLE_CHANCE_1X" in pref
        assert "DOUBLE_CHANCE_X2" in pref


# ---------------------------------------------------------------------------
# BOTH_OVER25_BTTS suppressed in Belgium
# ---------------------------------------------------------------------------

class TestBelgiumSuppression:
    def test_both_over25_btts_suppressed_in_profile(self):
        supp = LEAGUE_PROFILES["Belgian Pro League"]["suppressed_subtypes"]
        assert "BOTH_OVER25_BTTS" in supp

    def test_both_over25_btts_adjusted_strength_is_suppressed(self):
        rec = _minimal_rec("BOTH_OVER25_BTTS")
        result = apply_league_market_profile(rec, "Belgian Pro League")
        assert result["league_adjusted_strength"] == "SUPPRESSED"

    def test_both_over25_btts_warning_triggered(self):
        rec = _minimal_rec("BOTH_OVER25_BTTS")
        result = apply_league_market_profile(rec, "Belgian Pro League")
        assert result["league_warning_flags"] != ""

    def test_both_over25_btts_is_hard_nogo_in_belgium(self):
        rec = _minimal_rec("BOTH_OVER25_BTTS")
        rec = apply_league_market_profile(rec, "Belgian Pro League")
        tier_result = build_market_tier(rec)
        assert tier_result["market_tier"] == "HARD_NO_GO"

    def test_under35_is_not_suppressed_in_belgium(self):
        rec = _minimal_rec("UNDER_35", mtype="UNDER")
        result = apply_league_market_profile(rec, "Belgian Pro League")
        assert result["league_adjusted_strength"] != "SUPPRESSED"

    def test_under35_eligible_for_a_tier_in_belgium(self):
        """UNDER_35 + HIGH strength + no warning → A_TIER in Belgium."""
        rec = _minimal_rec("UNDER_35", mtype="UNDER")
        rec = apply_league_market_profile(rec, "Belgian Pro League")
        tier_result = build_market_tier(rec)
        assert tier_result["market_tier"] == "A_TIER"

    def test_double_chance_1x_eligible_for_a_tier_in_belgium(self):
        rec = _minimal_rec("DOUBLE_CHANCE_1X", mtype="DOUBLE_CHANCE")
        rec = apply_league_market_profile(rec, "Belgian Pro League")
        tier_result = build_market_tier(rec)
        assert tier_result["market_tier"] == "A_TIER"


# ---------------------------------------------------------------------------
# BOTH_OVER25_BTTS and BTTS suppressed in Brazil
# ---------------------------------------------------------------------------

class TestBrazilSuppression:
    def test_both_over25_btts_suppressed_in_brazil_profile(self):
        supp = LEAGUE_PROFILES["Brasileiro Serie A"]["suppressed_subtypes"]
        assert "BOTH_OVER25_BTTS" in supp

    def test_btts_suppressed_in_brazil_profile(self):
        supp = LEAGUE_PROFILES["Brasileiro Serie A"]["suppressed_subtypes"]
        assert "BTTS" in supp

    def test_both_over25_btts_adjusted_strength_suppressed_brazil(self):
        rec = _minimal_rec("BOTH_OVER25_BTTS")
        result = apply_league_market_profile(rec, "Brasileiro Serie A")
        assert result["league_adjusted_strength"] == "SUPPRESSED"

    def test_btts_adjusted_strength_suppressed_brazil(self):
        rec = _minimal_rec("BTTS", mtype="BTTS_OVER")
        result = apply_league_market_profile(rec, "Brasileiro Serie A")
        assert result["league_adjusted_strength"] == "SUPPRESSED"

    def test_both_over25_btts_warning_brazil(self):
        rec = _minimal_rec("BOTH_OVER25_BTTS")
        result = apply_league_market_profile(rec, "Brasileiro Serie A")
        assert result["league_warning_flags"] != ""

    def test_btts_warning_brazil(self):
        rec = _minimal_rec("BTTS", mtype="BTTS_OVER")
        result = apply_league_market_profile(rec, "Brasileiro Serie A")
        assert result["league_warning_flags"] != ""

    def test_both_over25_btts_hard_nogo_brazil(self):
        rec = _minimal_rec("BOTH_OVER25_BTTS")
        rec = apply_league_market_profile(rec, "Brasileiro Serie A")
        tier_result = build_market_tier(rec)
        assert tier_result["market_tier"] == "HARD_NO_GO"

    def test_under35_not_suppressed_in_brazil(self):
        rec = _minimal_rec("UNDER_35", mtype="UNDER")
        result = apply_league_market_profile(rec, "Brasileiro Serie A")
        assert result["league_adjusted_strength"] != "SUPPRESSED"

    def test_under35_eligible_for_a_tier_in_brazil(self):
        rec = _minimal_rec("UNDER_35", mtype="UNDER")
        rec = apply_league_market_profile(rec, "Brasileiro Serie A")
        tier_result = build_market_tier(rec)
        assert tier_result["market_tier"] == "A_TIER"

    def test_double_chance_1x_eligible_for_a_tier_in_brazil(self):
        rec = _minimal_rec("DOUBLE_CHANCE_1X", mtype="DOUBLE_CHANCE")
        rec = apply_league_market_profile(rec, "Brasileiro Serie A")
        tier_result = build_market_tier(rec)
        assert tier_result["market_tier"] == "A_TIER"

    def test_brazil_alias_matches_profile(self):
        """'Brazil' and 'Brasileiro Serie A' must resolve to the same profile."""
        r1 = apply_league_market_profile(_minimal_rec("UNDER_35", mtype="UNDER"), "Brazil")
        r2 = apply_league_market_profile(_minimal_rec("UNDER_35", mtype="UNDER"), "Brasileiro Serie A")
        assert r1["league_profile"] == r2["league_profile"]


# ---------------------------------------------------------------------------
# market_tier fields in daily report CSV output
# ---------------------------------------------------------------------------

class TestDailyReportMarketTierFields:
    """Verify that apply_league_market_profile + build_market_tier together produce
    the four market_tier fields expected in the CSV output for both leagues."""

    TIER_FIELDS = ("market_tier", "market_tier_score", "market_tier_reason", "market_tier_flags")

    def _simulate_row(self, league: str, subtype: str, mtype: str = "UNDER") -> dict:
        rec = _minimal_rec(subtype, mtype=mtype)
        rec = apply_league_market_profile(rec, league)
        rec = build_market_tier(rec)
        return rec

    def test_belgium_report_has_market_tier(self):
        row = self._simulate_row("Belgian Pro League", "UNDER_35")
        for field in self.TIER_FIELDS:
            assert field in row, f"Missing field: {field}"

    def test_belgium_report_market_tier_not_empty(self):
        row = self._simulate_row("Belgian Pro League", "UNDER_35")
        assert row["market_tier"] in ("A_TIER", "B_TIER", "C_TIER",
                                      "DOWNGRADE", "HARD_NO_GO", "OBSERVE_ONLY")

    def test_belgium_report_market_tier_score_is_int(self):
        row = self._simulate_row("Belgian Pro League", "UNDER_35")
        assert isinstance(row["market_tier_score"], int)
        assert 0 <= row["market_tier_score"] <= 100

    def test_brazil_report_has_market_tier(self):
        row = self._simulate_row("Brasileiro Serie A", "UNDER_35")
        for field in self.TIER_FIELDS:
            assert field in row, f"Missing field: {field}"

    def test_brazil_report_market_tier_not_empty(self):
        row = self._simulate_row("Brasileiro Serie A", "UNDER_35")
        assert row["market_tier"] in ("A_TIER", "B_TIER", "C_TIER",
                                      "DOWNGRADE", "HARD_NO_GO", "OBSERVE_ONLY")

    def test_brazil_report_market_tier_score_is_int(self):
        row = self._simulate_row("Brasileiro Serie A", "UNDER_35")
        assert isinstance(row["market_tier_score"], int)
        assert 0 <= row["market_tier_score"] <= 100

    def test_belgium_btts_over25_hard_nogo_in_csv(self):
        row = self._simulate_row("Belgian Pro League", "BOTH_OVER25_BTTS", mtype="BTTS_OVER")
        assert row["market_tier"] == "HARD_NO_GO"

    def test_brazil_btts_over25_hard_nogo_in_csv(self):
        row = self._simulate_row("Brasileiro Serie A", "BOTH_OVER25_BTTS", mtype="BTTS_OVER")
        assert row["market_tier"] == "HARD_NO_GO"
