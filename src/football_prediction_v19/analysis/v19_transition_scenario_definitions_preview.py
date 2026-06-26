# -*- coding: utf-8 -*-
"""Synthetic scenario definitions for the v1.9 decision transition lab."""
from __future__ import annotations

from copy import deepcopy


SAFETY = {
    "test_scenario_mode": True,
    "synthetic_completion_values": True,
    "not_real_match_data": True,
    "not_for_prediction": True,
    "network_calls_enabled": False,
    "betting_logic_enabled": False,
    "staking_logic_enabled": False,
    "roi_logic_enabled": False,
}


CRITICAL_FIELDS = {
    "home_recent_xg_for": "1.10",
    "away_recent_xg_for": "1.85",
    "home_recent_xg_against": "1.45",
    "away_recent_xg_against": "1.05",
    "home_big_chances_for": "6",
    "away_big_chances_for": "11",
    "home_big_chances_against": "9",
    "away_big_chances_against": "5",
    "home_goalkeeper_status": "AVAILABLE",
    "away_goalkeeper_status": "AVAILABLE",
    "home_missing_players": "verified scenario none",
    "away_missing_players": "verified scenario none",
    "home_suspended_players": "verified scenario none",
    "away_suspended_players": "verified scenario none",
    "home_doubtful_players": "verified scenario none",
    "away_doubtful_players": "verified scenario none",
    "home_open_odds": "3.40",
    "draw_open_odds": "3.30",
    "away_open_odds": "2.20",
    "home_closing_odds": "3.55",
    "draw_closing_odds": "3.25",
    "away_closing_odds": "2.05",
    "dnb_home_odds": "2.40",
    "dnb_away_odds": "1.65",
    "over_line": "2.5",
    "over_current_odds": "1.92",
    "under_current_odds": "1.90",
}


def transition_scenarios() -> list[dict[str, object]]:
    scenarios = [
        {
            "scenario_id": "EMPTY_COMPLETION_CONTROL",
            "scenario_name": "Empty completion control",
            "scenario_type": "CONTROL",
            "description": "No synthetic values are filled; the decision should remain unchanged.",
            "synthetic_values": {},
            "expected_final_decision_class": "ANALYST_LEAN_ONLY",
            "expected_promotion_allowed": False,
            "expected_strong_promotion_allowed": False,
            "expected_conflict_score": "HIGH",
            "expected_removed_blockers": [],
            "expected_remaining_blockers": ["missing recent form", "missing big chances", "missing full availability details", "missing opening/closing odds", "missing DNB/OU odds", "productive betting safety disabled"],
            "expected_market_family_changes": [],
        },
        {
            "scenario_id": "POSITIVE_ALIGNMENT_CANDIDATE",
            "scenario_name": "Positive alignment candidate",
            "scenario_type": "PROMOTION",
            "description": "Critical data is complete and lightly supports Atalanta.",
            "synthetic_values": CRITICAL_FIELDS,
            "expected_final_decision_class": "BET_CANDIDATE_PREVIEW",
            "expected_promotion_allowed": True,
            "expected_strong_promotion_allowed": False,
            "expected_conflict_score": "MEDIUM",
            "expected_removed_blockers": ["missing recent form", "missing big chances", "missing full availability details", "missing opening/closing odds", "missing DNB/OU odds"],
            "expected_remaining_blockers": ["productive betting safety disabled"],
            "expected_market_family_changes": ["1X2"],
        },
        {
            "scenario_id": "STRONG_ALIGNMENT_LOW_CONFLICT",
            "scenario_name": "Strong alignment low conflict",
            "scenario_type": "STRONG_PROMOTION",
            "description": "Critical data is complete, strongly aligned, and lowers conflict.",
            "synthetic_values": {**CRITICAL_FIELDS, "away_recent_xg_for": "2.25", "home_recent_xg_against": "1.80", "away_closing_odds": "1.95"},
            "expected_final_decision_class": "STRONG_BET_CANDIDATE_PREVIEW",
            "expected_promotion_allowed": True,
            "expected_strong_promotion_allowed": True,
            "expected_conflict_score": "LOW",
            "expected_removed_blockers": ["missing recent form", "missing big chances", "missing full availability details", "missing opening/closing odds", "missing DNB/OU odds"],
            "expected_remaining_blockers": ["productive betting safety disabled"],
            "expected_market_family_changes": ["1X2", "Double Chance"],
        },
        {
            "scenario_id": "NEGATIVE_ALIGNMENT_NO_BET",
            "scenario_name": "Negative alignment no bet",
            "scenario_type": "DOWNGRADE",
            "description": "Recent form, big chances, availability, and market drift all oppose Atalanta.",
            "synthetic_values": {**CRITICAL_FIELDS, "home_recent_xg_for": "2.05", "away_recent_xg_for": "0.95", "away_missing_players": "scenario key attackers missing", "away_closing_odds": "2.70"},
            "expected_final_decision_class": "NO_BET_RECOMMENDED",
            "expected_promotion_allowed": False,
            "expected_strong_promotion_allowed": False,
            "expected_conflict_score": "HIGH",
            "expected_removed_blockers": ["missing recent form", "missing big chances", "missing full availability details", "missing opening/closing odds", "missing DNB/OU odds"],
            "expected_remaining_blockers": ["productive betting safety disabled"],
            "expected_market_family_changes": ["No-Bet"],
        },
        {
            "scenario_id": "MIXED_ALIGNMENT_CONFLICT_REVIEW",
            "scenario_name": "Mixed alignment conflict review",
            "scenario_type": "CONFLICT",
            "description": "Some values support Atalanta while market and availability are unclear.",
            "synthetic_values": {**CRITICAL_FIELDS, "home_big_chances_for": "10", "away_big_chances_for": "10", "away_doubtful_players": "scenario uncertainty", "away_closing_odds": "2.35"},
            "expected_final_decision_class": "CONFLICT_REVIEW",
            "expected_promotion_allowed": False,
            "expected_strong_promotion_allowed": False,
            "expected_conflict_score": "HIGH",
            "expected_removed_blockers": ["missing recent form", "missing big chances", "missing full availability details", "missing opening/closing odds", "missing DNB/OU odds"],
            "expected_remaining_blockers": ["productive betting safety disabled"],
            "expected_market_family_changes": ["1X2"],
        },
        {
            "scenario_id": "MARKET_DRIFT_DOWNGRADE",
            "scenario_name": "Market drift downgrade",
            "scenario_type": "DOWNGRADE",
            "description": "Sporting data aligns, but market drift blocks promotion.",
            "synthetic_values": {**CRITICAL_FIELDS, "away_open_odds": "2.05", "away_closing_odds": "2.75"},
            "expected_final_decision_class": "NO_BET_RECOMMENDED",
            "expected_promotion_allowed": False,
            "expected_strong_promotion_allowed": False,
            "expected_conflict_score": "MEDIUM_HIGH",
            "expected_removed_blockers": ["missing recent form", "missing big chances", "missing full availability details", "missing opening/closing odds", "missing DNB/OU odds"],
            "expected_remaining_blockers": ["productive betting safety disabled"],
            "expected_market_family_changes": ["1X2"],
        },
        {
            "scenario_id": "AVAILABILITY_DOWNGRADE",
            "scenario_name": "Availability downgrade",
            "scenario_type": "DOWNGRADE",
            "description": "Sporting data aligns, but Atalanta availability is negative.",
            "synthetic_values": {**CRITICAL_FIELDS, "away_goalkeeper_status": "DOUBTFUL", "away_missing_players": "scenario key attackers missing"},
            "expected_final_decision_class": "NO_BET_RECOMMENDED",
            "expected_promotion_allowed": False,
            "expected_strong_promotion_allowed": False,
            "expected_conflict_score": "HIGH",
            "expected_removed_blockers": ["missing recent form", "missing big chances", "missing full availability details", "missing opening/closing odds", "missing DNB/OU odds"],
            "expected_remaining_blockers": ["productive betting safety disabled"],
            "expected_market_family_changes": ["No-Bet"],
        },
    ]
    output = []
    for scenario in scenarios:
        item = deepcopy(scenario)
        item["safety"] = SAFETY.copy()
        output.append(item)
    return output
