"""Tests for the league-aware diagnostic report profile layer.

Covers:
- La Liga UNDER_35 promoted
- La Liga OVER_25 suppressed
- Serie A UNDER_35 promoted
- Eredivisie OVER_25 allowed/promoted
- Eredivisie BOTH_OVER25_BTTS suppressed
- 2.Bundesliga AVOID promoted
- Premier League OVER_25 standalone suppressed
- Ligue 1 DIRECTION gets warning
- Existing type/subtype fields not removed
- Unknown league returns neutral profile safely
"""

import pytest
from football_prediction_v19.diagnostics.league_market_profiles import (
    apply_league_market_profile,
    LEAGUE_PROFILES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rec(
    market_type: str = "AVOID",
    market_subtype: str = "NONE",
    strength: str = "MODERATE",
    extra: dict | None = None,
) -> dict:
    """Build a minimal recommendation dict."""
    base = {
        "recommended_market_type": market_type,
        "recommended_market_subtype": market_subtype,
        "recommendation_strength": strength,
        "model_home_prob": 0.45,
        "model_draw_prob": 0.30,
        "model_away_prob": 0.25,
    }
    if extra:
        base.update(extra)
    return base


# ---------------------------------------------------------------------------
# La Liga
# ---------------------------------------------------------------------------

def test_la_liga_under35_promoted():
    rec = _rec("UNDER", "UNDER_35", "MODERATE")
    result = apply_league_market_profile(rec, "La Liga")
    assert result["league_adjusted_strength"] == "HIGH"
    assert "UNDER_35" in result["league_preferred_subtype"]
    assert result["league_profile"] == "la_liga_control"


def test_la_liga_over25_suppressed():
    rec = _rec("BTTS_OVER", "OVER_25", "STRONG")
    result = apply_league_market_profile(rec, "La Liga")
    assert result["league_adjusted_strength"] == "SUPPRESSED"
    assert "OVER_25" in result["league_suppressed_subtype"]


def test_la_liga_over25_warning_flag():
    rec = _rec("BTTS_OVER", "OVER_25")
    result = apply_league_market_profile(rec, "La Liga")
    assert result["league_warning_flags"] != ""
    assert "La Liga" in result["league_warning_flags"]


def test_la_liga_btts_suppressed():
    rec = _rec("BTTS_OVER", "BTTS")
    result = apply_league_market_profile(rec, "La Liga")
    assert result["league_adjusted_strength"] == "SUPPRESSED"


def test_la_liga_avoid_promoted():
    rec = _rec("AVOID", "AVOID_VOLATILE")
    result = apply_league_market_profile(rec, "La Liga")
    assert result["league_adjusted_strength"] == "HIGH"


# ---------------------------------------------------------------------------
# Serie A
# ---------------------------------------------------------------------------

def test_serie_a_under35_promoted():
    rec = _rec("UNDER", "UNDER_35", "MODERATE")
    result = apply_league_market_profile(rec, "Serie A")
    assert result["league_adjusted_strength"] == "HIGH"
    assert result["league_profile"] == "serie_a_control"


def test_serie_a_both_over25_btts_suppressed():
    rec = _rec("BTTS_OVER", "BOTH_OVER25_BTTS", "STRONG")
    result = apply_league_market_profile(rec, "Serie A")
    assert result["league_adjusted_strength"] == "SUPPRESSED"


def test_serie_a_btts_allowed():
    rec = _rec("BTTS_OVER", "BTTS", "MODERATE")
    result = apply_league_market_profile(rec, "Serie A")
    # BTTS is allowed but not preferred — should NOT be suppressed
    assert result["league_adjusted_strength"] != "SUPPRESSED"


# ---------------------------------------------------------------------------
# Eredivisie
# ---------------------------------------------------------------------------

def test_eredivisie_over25_promoted():
    rec = _rec("BTTS_OVER", "OVER_25", "MODERATE")
    result = apply_league_market_profile(rec, "Eredivisie")
    # OVER_25 is in allowed_subtypes for Eredivisie — not suppressed
    assert result["league_adjusted_strength"] != "SUPPRESSED"
    assert result["league_profile"] == "eredivisie_goals"


def test_eredivisie_over25_no_warning():
    rec = _rec("BTTS_OVER", "OVER_25")
    result = apply_league_market_profile(rec, "Eredivisie")
    # No warning for OVER_25 in Eredivisie (it's allowed)
    assert "OVER_25" not in result["league_warning_flags"]


def test_eredivisie_both_over25_btts_suppressed():
    rec = _rec("BTTS_OVER", "BOTH_OVER25_BTTS", "STRONG")
    result = apply_league_market_profile(rec, "Eredivisie")
    assert result["league_adjusted_strength"] == "SUPPRESSED"
    assert result["league_warning_flags"] != ""


def test_eredivisie_dc_promoted():
    rec = _rec("DOUBLE_CHANCE", "DOUBLE_CHANCE_1X", "MODERATE")
    result = apply_league_market_profile(rec, "Eredivisie")
    assert result["league_adjusted_strength"] == "HIGH"


# ---------------------------------------------------------------------------
# 2.Bundesliga
# ---------------------------------------------------------------------------

def test_bundesliga2_avoid_promoted():
    rec = _rec("AVOID", "AVOID_VOLATILE", "MODERATE")
    result = apply_league_market_profile(rec, "2. Bundesliga")
    assert result["league_adjusted_strength"] == "HIGH"
    assert result["league_profile"] == "bundesliga2_goals_volatile"


def test_bundesliga2_under35_suppressed():
    rec = _rec("UNDER", "UNDER_35", "STRONG")
    result = apply_league_market_profile(rec, "2. Bundesliga")
    assert result["league_adjusted_strength"] == "SUPPRESSED"


def test_bundesliga2_both_over25_btts_suppressed():
    rec = _rec("BTTS_OVER", "BOTH_OVER25_BTTS", "STRONG")
    result = apply_league_market_profile(rec, "2. Bundesliga")
    assert result["league_adjusted_strength"] == "SUPPRESSED"


# ---------------------------------------------------------------------------
# Premier League
# ---------------------------------------------------------------------------

def test_premier_league_over25_standalone_suppressed():
    rec = _rec("BTTS_OVER", "OVER_25", "STRONG")
    result = apply_league_market_profile(rec, "Premier League")
    assert result["league_adjusted_strength"] == "SUPPRESSED"
    assert result["league_profile"] == "premier_league_balanced"


def test_premier_league_dc_promoted():
    rec = _rec("DOUBLE_CHANCE", "DOUBLE_CHANCE_X2", "MODERATE")
    result = apply_league_market_profile(rec, "Premier League")
    assert result["league_adjusted_strength"] == "HIGH"


def test_premier_league_btts_allowed():
    rec = _rec("BTTS_OVER", "BTTS", "MODERATE")
    result = apply_league_market_profile(rec, "Premier League")
    assert result["league_adjusted_strength"] != "SUPPRESSED"


# ---------------------------------------------------------------------------
# Ligue 1
# ---------------------------------------------------------------------------

def test_ligue1_direction_warning():
    rec = _rec("DIRECTION", "DIRECTION_HOME", "MODERATE")
    result = apply_league_market_profile(rec, "Ligue 1")
    assert result["league_warning_flags"] != ""
    assert "DIRECTION" in result["league_warning_flags"] or "Ligue 1" in result["league_warning_flags"]
    assert result["league_profile"] == "ligue1_cautious"


def test_ligue1_avoid_promoted():
    rec = _rec("AVOID", "AVOID_LOW_CONTROL", "MODERATE")
    result = apply_league_market_profile(rec, "Ligue 1")
    assert result["league_adjusted_strength"] == "HIGH"


def test_ligue1_over25_suppressed():
    rec = _rec("BTTS_OVER", "OVER_25", "STRONG")
    result = apply_league_market_profile(rec, "Ligue 1")
    assert result["league_adjusted_strength"] == "SUPPRESSED"


# ---------------------------------------------------------------------------
# Invariant: existing fields are never removed
# ---------------------------------------------------------------------------

def test_existing_fields_preserved():
    rec = _rec("UNDER", "UNDER_35", "STRONG", extra={"home_team": "FC Barcelona", "date": "2024-01-01"})
    result = apply_league_market_profile(rec, "La Liga")
    # All original keys still present
    for key in rec:
        assert key in result, f"Field '{key}' was removed by apply_league_market_profile"
    # Core market fields unchanged
    assert result["recommended_market_type"] == "UNDER"
    assert result["recommended_market_subtype"] == "UNDER_35"
    assert result["recommendation_strength"] == "STRONG"


def test_market_type_and_subtype_unchanged():
    """recommended_market_type and recommended_market_subtype must never be modified."""
    for league in LEAGUE_PROFILES:
        rec = _rec("BTTS_OVER", "BOTH_OVER25_BTTS", "STRONG")
        result = apply_league_market_profile(rec, league)
        assert result["recommended_market_type"] == "BTTS_OVER"
        assert result["recommended_market_subtype"] == "BOTH_OVER25_BTTS"


# ---------------------------------------------------------------------------
# Unknown league returns neutral / safe result
# ---------------------------------------------------------------------------

def test_unknown_league_safe():
    rec = _rec("AVOID", "AVOID_VOLATILE", "MODERATE")
    result = apply_league_market_profile(rec, "Galactic League")
    assert result["league_profile"] == "unknown_league"
    assert result["league_adjusted_strength"] in {"HIGH", "MEDIUM", "LOW", "SUPPRESSED"}
    assert result["league_warning_flags"] == ""
    # All new fields present
    for field in [
        "league_profile",
        "league_adjusted_strength",
        "league_profile_note",
        "league_warning_flags",
        "league_preferred_subtype",
        "league_suppressed_subtype",
    ]:
        assert field in result, f"Missing field '{field}' for unknown league"


def test_empty_league_string_safe():
    rec = _rec()
    result = apply_league_market_profile(rec, "")
    assert result["league_profile"] == "unknown_league"


def test_none_like_recommendation_values_safe():
    """Gracefully handle missing/None recommendation fields."""
    rec = {
        "recommended_market_type": None,
        "recommended_market_subtype": None,
        "recommendation_strength": None,
    }
    result = apply_league_market_profile(rec, "La Liga")
    assert "league_profile" in result
    assert result["league_adjusted_strength"] in {"HIGH", "MEDIUM", "LOW", "SUPPRESSED"}


# ---------------------------------------------------------------------------
# New fields completeness
# ---------------------------------------------------------------------------

def test_all_new_fields_present_for_all_leagues():
    required_new = {
        "league_profile",
        "league_adjusted_strength",
        "league_profile_note",
        "league_warning_flags",
        "league_preferred_subtype",
        "league_suppressed_subtype",
    }
    for league in list(LEAGUE_PROFILES.keys()) + ["Unknown"]:
        rec = _rec()
        result = apply_league_market_profile(rec, league)
        missing = required_new - set(result.keys())
        assert not missing, f"Missing fields for '{league}': {missing}"


def test_league_profile_note_is_string():
    result = apply_league_market_profile(_rec(), "Eredivisie")
    assert isinstance(result["league_profile_note"], str)
    assert len(result["league_profile_note"]) > 10
