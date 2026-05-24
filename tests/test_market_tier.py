# -*- coding: utf-8 -*-
"""Tests for diagnostics.market_tier.build_market_tier.

Verifies tier classification, score ranges, field preservation,
and graceful handling of missing/None data.

No betting rules, no ROI, no model probability changes.
"""

from __future__ import annotations

import pytest

from football_prediction_v19.diagnostics import build_market_tier, MARKET_TIERS
from football_prediction_v19.diagnostics.market_tier import (
    _A_TIER_SUBTYPES,
    _HARD_NOGO_SUBTYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rec(
    mtype: str = "UNDER",
    subtype: str = "UNDER_35",
    strength: str = "HIGH",
    profile: str = "la_liga_control",
    league: str = "La Liga",
    warning: str = "",
    confidence: str = "HIGH",
    data_warning: bool = False,
    chaos: float | None = 3.0,
    preferred: str = "UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
    suppressed: str = "OVER_25, BTTS, BOTH_OVER25_BTTS",
) -> dict:
    """Build a minimal recommendation dict for testing."""
    return {
        "recommended_market_type": mtype,
        "recommended_market_subtype": subtype,
        "recommended_market_read": "test read",
        "recommendation_strength": "STRONG",
        "risk_note": "",
        "league": league,
        "league_profile": profile,
        "league_adjusted_strength": strength,
        "league_warning_flags": warning,
        "league_preferred_subtype": preferred,
        "league_suppressed_subtype": suppressed,
        "confidence": confidence,
        "data_warning": data_warning,
        "chaos_score_10": chaos,
    }


# ---------------------------------------------------------------------------
# A_TIER cases
# ---------------------------------------------------------------------------

class TestATier:
    def test_under35_high_no_warning_is_a_tier(self):
        result = build_market_tier(_rec(subtype="UNDER_35"))
        assert result["market_tier"] == "A_TIER"

    def test_double_chance_1x_high_no_warning_is_a_tier(self):
        result = build_market_tier(_rec(mtype="DOUBLE_CHANCE", subtype="DOUBLE_CHANCE_1X"))
        assert result["market_tier"] == "A_TIER"

    def test_double_chance_x2_high_no_warning_is_a_tier(self):
        result = build_market_tier(_rec(mtype="DOUBLE_CHANCE", subtype="DOUBLE_CHANCE_X2"))
        assert result["market_tier"] == "A_TIER"

    def test_a_tier_score_in_range(self):
        result = build_market_tier(_rec(subtype="UNDER_35"))
        assert 65 <= result["market_tier_score"] <= 100

    def test_a_tier_reason_not_empty(self):
        result = build_market_tier(_rec(subtype="UNDER_35"))
        assert len(result["market_tier_reason"]) > 0

    def test_a_tier_blocked_by_warning(self):
        result = build_market_tier(_rec(subtype="UNDER_35", warning="some warning"))
        assert result["market_tier"] != "A_TIER"

    def test_a_tier_blocked_by_medium_strength(self):
        result = build_market_tier(_rec(subtype="UNDER_35", strength="MEDIUM"))
        assert result["market_tier"] != "A_TIER"

    def test_a_tier_blocked_by_high_chaos(self):
        result = build_market_tier(_rec(subtype="UNDER_35", chaos=7.5))
        assert result["market_tier"] != "A_TIER"

    def test_ligue1_excluded_from_a_tier(self):
        result = build_market_tier(_rec(
            subtype="DOUBLE_CHANCE_1X",
            league="Ligue 1",
            profile="ligue1_cautious",
            suppressed="BOTH_OVER25_BTTS, OVER_25",
        ))
        assert result["market_tier"] != "A_TIER"

    def test_serie_a_under35_is_a_tier(self):
        result = build_market_tier(_rec(
            subtype="UNDER_35",
            league="Serie A",
            profile="serie_a_control",
            preferred="UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
            suppressed="BOTH_OVER25_BTTS",
        ))
        assert result["market_tier"] == "A_TIER"


# ---------------------------------------------------------------------------
# HARD_NO_GO cases
# ---------------------------------------------------------------------------

class TestHardNoGo:
    def test_both_over25_btts_is_hard_nogo(self):
        result = build_market_tier(_rec(
            mtype="BTTS_OVER",
            subtype="BOTH_OVER25_BTTS",
            strength="HIGH",
            warning="",
        ))
        assert result["market_tier"] == "HARD_NO_GO"

    def test_suppressed_plus_warning_is_hard_nogo(self):
        result = build_market_tier(_rec(
            subtype="OVER_25",
            strength="SUPPRESSED",
            warning="La Liga: goals subtype has poor walk-forward evidence.",
        ))
        assert result["market_tier"] == "HARD_NO_GO"

    def test_ligue1_direction_is_hard_nogo(self):
        result = build_market_tier(_rec(
            mtype="DIRECTION",
            subtype="DIRECTION_HOME",
            league="Ligue 1",
            profile="ligue1_cautious",
            strength="MEDIUM",
            warning="Ligue 1: DIRECTION type has historically poor accuracy.",
            suppressed="BOTH_OVER25_BTTS, OVER_25",
        ))
        assert result["market_tier"] == "HARD_NO_GO"

    def test_hard_nogo_score_under_25(self):
        result = build_market_tier(_rec(subtype="BOTH_OVER25_BTTS"))
        assert result["market_tier_score"] <= 24

    def test_hard_nogo_flags_not_empty(self):
        result = build_market_tier(_rec(subtype="BOTH_OVER25_BTTS"))
        assert len(result["market_tier_flags"]) > 0


# ---------------------------------------------------------------------------
# DOWNGRADE cases
# ---------------------------------------------------------------------------

class TestDowngrade:
    def test_btts_alone_is_downgrade(self):
        result = build_market_tier(_rec(
            mtype="BTTS_OVER",
            subtype="BTTS",
            strength="HIGH",
            warning="",
            profile="premier_league_balanced",
            league="Premier League",
            preferred="DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
            suppressed="OVER_25, BOTH_OVER25_BTTS",
        ))
        assert result["market_tier"] == "DOWNGRADE"

    def test_over25_outside_goal_friendly_is_downgrade(self):
        result = build_market_tier(_rec(
            mtype="BTTS_OVER",
            subtype="OVER_25",
            strength="HIGH",
            warning="",
            league="La Liga",
            profile="la_liga_control",
            preferred="UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
            suppressed="OVER_25, BTTS, BOTH_OVER25_BTTS",
        ))
        assert result["market_tier"] == "DOWNGRADE"

    def test_over25_eredivisie_not_downgrade(self):
        result = build_market_tier(_rec(
            mtype="BTTS_OVER",
            subtype="OVER_25",
            strength="HIGH",
            warning="",
            league="Eredivisie",
            profile="eredivisie_goals",
            preferred="OVER_25, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
            suppressed="BOTH_OVER25_BTTS",
        ))
        assert result["market_tier"] not in ("DOWNGRADE", "HARD_NO_GO")

    def test_over25_premier_league_not_downgrade(self):
        """User spec: OVER_25 in Premier League is not automatically no-go."""
        result = build_market_tier(_rec(
            mtype="BTTS_OVER",
            subtype="OVER_25",
            strength="HIGH",
            warning="",
            league="Premier League",
            profile="premier_league_balanced",
            preferred="DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
            suppressed="OVER_25, BOTH_OVER25_BTTS",
        ))
        assert result["market_tier"] not in ("HARD_NO_GO",)

    def test_over25_2bundesliga_not_downgrade(self):
        result = build_market_tier(_rec(
            mtype="BTTS_OVER",
            subtype="OVER_25",
            strength="HIGH",
            warning="",
            league="2. Bundesliga",
            profile="bundesliga2_goals_volatile",
            preferred="DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
            suppressed="UNDER_35, BOTH_OVER25_BTTS",
        ))
        assert result["market_tier"] not in ("HARD_NO_GO",)

    def test_warning_flag_causes_downgrade(self):
        result = build_market_tier(_rec(
            subtype="DOUBLE_CHANCE_1X",
            strength="HIGH",
            warning="Premier League: OVER_25 standalone and BOTH_OVER25_BTTS have poor evidence.",
            league="Premier League",
            profile="premier_league_balanced",
        ))
        # With a warning flag, should not be A_TIER; should be DOWNGRADE or lower
        assert result["market_tier"] in ("B_TIER", "DOWNGRADE", "C_TIER", "HARD_NO_GO")

    def test_downgrade_score_range(self):
        result = build_market_tier(_rec(
            subtype="BTTS",
            league="Serie A",
            profile="serie_a_control",
        ))
        assert result["market_tier"] == "DOWNGRADE"
        assert 15 <= result["market_tier_score"] <= 44


# ---------------------------------------------------------------------------
# OBSERVE_ONLY cases
# ---------------------------------------------------------------------------

class TestObserveOnly:
    def test_observe_only_type_preserved(self):
        result = build_market_tier(_rec(mtype="OBSERVE_ONLY", subtype="NONE"))
        assert result["market_tier"] == "OBSERVE_ONLY"

    def test_observe_only_no_confidence_plus_data_warning(self):
        result = build_market_tier(_rec(
            confidence="NO-CONFIDENCE",
            data_warning=True,
        ))
        assert result["market_tier"] == "OBSERVE_ONLY"


# ---------------------------------------------------------------------------
# Existing fields not removed
# ---------------------------------------------------------------------------

class TestFieldPreservation:
    def test_existing_fields_preserved(self):
        rec = _rec()
        before_keys = set(rec.keys())
        result = build_market_tier(rec)
        # All original keys must still be present
        assert before_keys.issubset(set(result.keys()))

    def test_recommended_market_type_unchanged(self):
        rec = _rec(mtype="UNDER", subtype="UNDER_35")
        result = build_market_tier(rec)
        assert result["recommended_market_type"] == "UNDER"

    def test_recommended_market_subtype_unchanged(self):
        rec = _rec(subtype="DOUBLE_CHANCE_1X")
        result = build_market_tier(rec)
        assert result["recommended_market_subtype"] == "DOUBLE_CHANCE_1X"

    def test_four_new_fields_always_present(self):
        rec = _rec()
        result = build_market_tier(rec)
        for field in ("market_tier", "market_tier_score", "market_tier_reason", "market_tier_flags"):
            assert field in result, f"Missing field: {field}"

    def test_tier_always_valid_value(self):
        for subtype in ["UNDER_35", "DOUBLE_CHANCE_1X", "BTTS", "BOTH_OVER25_BTTS", "OVER_25"]:
            result = build_market_tier(_rec(subtype=subtype))
            assert result["market_tier"] in MARKET_TIERS

    def test_none_values_safe(self):
        """Function must not crash when optional fields are None."""
        result = build_market_tier({
            "recommended_market_type": None,
            "recommended_market_subtype": None,
            "league_adjusted_strength": None,
            "league_warning_flags": None,
            "chaos_score_10": None,
        })
        assert result["market_tier"] in MARKET_TIERS
        assert isinstance(result["market_tier_score"], int)

    def test_empty_dict_safe(self):
        """Function must handle a completely empty recommendation dict."""
        result = build_market_tier({})
        assert result["market_tier"] in MARKET_TIERS
        assert 0 <= result["market_tier_score"] <= 100

    def test_score_always_in_0_100(self):
        cases = [
            _rec(subtype="UNDER_35"),
            _rec(subtype="BOTH_OVER25_BTTS"),
            _rec(subtype="BTTS"),
            _rec(strength="SUPPRESSED", warning="some warning"),
            _rec(mtype="OBSERVE_ONLY"),
            {},
        ]
        for rec in cases:
            result = build_market_tier(rec)
            assert 0 <= result["market_tier_score"] <= 100, (
                f"Score out of range for {rec}: {result['market_tier_score']}"
            )


# ---------------------------------------------------------------------------
# MARKET_TIERS constant
# ---------------------------------------------------------------------------

class TestConstants:
    def test_market_tiers_tuple_contains_all_expected(self):
        expected = {"A_TIER", "B_TIER", "C_TIER", "DOWNGRADE", "HARD_NO_GO", "OBSERVE_ONLY"}
        assert expected == set(MARKET_TIERS)

    def test_a_tier_subtypes_complete(self):
        assert "UNDER_35" in _A_TIER_SUBTYPES
        assert "DOUBLE_CHANCE_1X" in _A_TIER_SUBTYPES
        assert "DOUBLE_CHANCE_X2" in _A_TIER_SUBTYPES

    def test_hard_nogo_subtypes_includes_both_over25_btts(self):
        assert "BOTH_OVER25_BTTS" in _HARD_NOGO_SUBTYPES
