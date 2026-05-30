# -*- coding: utf-8 -*-
"""Tests for Phase 11.3 defensive tier rules.

Diagnostic/reporting only: no probability, market type, subtype, staking, or
ROI behavior is changed here.
"""

from __future__ import annotations

from football_prediction_v19.diagnostics import build_market_tier


def _rec(
    *,
    mtype: str = "BTTS_OVER",
    subtype: str = "BTTS",
    strength: str = "HIGH",
    ctrl_bucket: str = "medium (5-7)",
    odds_bucket: str = "long_or_even",
    season_phase: str = "mid",
) -> dict:
    return {
        "recommended_market_type": mtype,
        "recommended_market_subtype": subtype,
        "recommended_market_read": "test read",
        "recommendation_strength": "STRONG",
        "risk_note": "keep me",
        "league": "Serie A",
        "league_profile": "serie_a_control",
        "league_adjusted_strength": strength,
        "league_warning_flags": "",
        "league_preferred_subtype": "UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2",
        "league_suppressed_subtype": "OVER_25, BTTS, BOTH_OVER25_BTTS",
        "confidence": "HIGH",
        "data_warning": False,
        "chaos_score_10": 3.0,
        "ctrl_bucket": ctrl_bucket,
        "odds_bucket": odds_bucket,
        "season_phase": season_phase,
        "model_home_prob": 0.52,
        "model_draw_prob": 0.25,
        "model_away_prob": 0.23,
    }


def _assert_preserved(result: dict) -> None:
    assert result["recommended_market_type"] == "BTTS_OVER"
    assert result["recommended_market_subtype"] == "BTTS"
    assert result["model_home_prob"] == 0.52
    assert result["model_draw_prob"] == 0.25
    assert result["model_away_prob"] == 0.23


def test_downgrade_low_control_becomes_hard_no_go():
    result = build_market_tier(_rec(ctrl_bucket="low (3-5)"))

    assert result["market_tier"] == "HARD_NO_GO"
    assert "phase_11_3_downgrade_low_control_no_go" in result["market_tier_flags"]
    assert "phase_11_3_downgrade_low_control_no_go" in result["market_tier_reason"]
    _assert_preserved(result)


def test_downgrade_medium_fav_becomes_hard_no_go():
    result = build_market_tier(_rec(odds_bucket="medium_fav (2.0-2.5)"))

    assert result["market_tier"] == "HARD_NO_GO"
    assert "phase_11_3_downgrade_medium_fav_no_go" in result["market_tier_flags"]
    _assert_preserved(result)


def test_downgrade_late_season_becomes_hard_no_go():
    result = build_market_tier(_rec(season_phase="late"))

    assert result["market_tier"] == "HARD_NO_GO"
    assert "phase_11_3_downgrade_late_season_no_go" in result["market_tier_flags"]
    _assert_preserved(result)


def test_multiple_phase_11_3_flags_are_appended():
    result = build_market_tier(_rec(
        ctrl_bucket="low (3-5)",
        odds_bucket="medium_fav (2.0-2.5)",
        season_phase="late",
    ))

    assert result["market_tier"] == "HARD_NO_GO"
    assert "phase_11_3_downgrade_low_control_no_go" in result["market_tier_flags"]
    assert "phase_11_3_downgrade_medium_fav_no_go" in result["market_tier_flags"]
    assert "phase_11_3_downgrade_late_season_no_go" in result["market_tier_flags"]


def test_hard_no_go_low_control_remains_hard_no_go_and_gets_confirmed_flag():
    result = build_market_tier(_rec(
        subtype="BOTH_OVER25_BTTS",
        ctrl_bucket="low (3-5)",
    ))

    assert result["market_tier"] == "HARD_NO_GO"
    assert "phase_11_3_hard_no_go_low_control_confirmed" in result["market_tier_flags"]


def test_hard_no_go_medium_fav_remains_hard_no_go_and_gets_confirmed_flag():
    result = build_market_tier(_rec(
        subtype="BOTH_OVER25_BTTS",
        odds_bucket="medium_fav (2.0-2.5)",
    ))

    assert result["market_tier"] == "HARD_NO_GO"
    assert "phase_11_3_hard_no_go_medium_fav_confirmed" in result["market_tier_flags"]


def test_a_tier_low_control_is_not_changed():
    result = build_market_tier(_rec(
        mtype="UNDER",
        subtype="UNDER_35",
        ctrl_bucket="low (3-5)",
    ))

    assert result["market_tier"] == "A_TIER"
    assert "phase_11_3" not in result["market_tier_flags"]


def test_b_tier_medium_fav_is_not_changed():
    result = build_market_tier(_rec(
        mtype="UNDER",
        subtype="UNDER_35",
        strength="MEDIUM",
        odds_bucket="medium_fav (2.0-2.5)",
    ))

    assert result["market_tier"] == "B_TIER"
    assert "phase_11_3" not in result["market_tier_flags"]


def test_recommended_market_type_and_subtype_remain_unchanged():
    result = build_market_tier(_rec(ctrl_bucket="low (3-5)"))

    assert result["recommended_market_type"] == "BTTS_OVER"
    assert result["recommended_market_subtype"] == "BTTS"


def test_probabilities_remain_unchanged():
    result = build_market_tier(_rec(odds_bucket="medium_fav (2.0-2.5)"))

    assert result["model_home_prob"] == 0.52
    assert result["model_draw_prob"] == 0.25
    assert result["model_away_prob"] == 0.23
