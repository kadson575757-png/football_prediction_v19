# -*- coding: utf-8 -*-
from __future__ import annotations

from football_prediction_v19.analysis.v19_portfolio_delta_preview import compute_portfolio_delta


def test_portfolio_delta_empty_completion_is_unchanged() -> None:
    base = {
        "matches": [
            {
                "match_id": "lazio_atalanta_2026_02_14",
                "status": "SUCCESS",
                "final_decision_class": "ANALYST_LEAN_ONLY",
                "promotion_allowed": False,
                "evidence_readiness_score": 85,
                "critical_blockers_count": 6,
            }
        ]
    }
    result = compute_portfolio_delta(base, base, missing_fields_filled_total=0)

    assert result.portfolio_delta_status == "V19_PORTFOLIO_DELTA_PREVIEW_READY"
    assert result.candidate_count_delta == 0
    assert result.average_readiness_delta == 0
    assert result.matches_unchanged == ["lazio_atalanta_2026_02_14"]
    assert result.final_summary == "No filled values; portfolio unchanged."
    assert result.network_calls_enabled is False
    assert result.betting_logic_enabled is False
    assert result.staking_logic_enabled is False
    assert result.roi_logic_enabled is False


def test_portfolio_delta_detects_candidate_upgrade_without_roi_or_stakes() -> None:
    base = {
        "matches": [
            {
                "match_id": "match-1",
                "status": "SUCCESS",
                "final_decision_class": "ANALYST_LEAN_ONLY",
                "promotion_allowed": False,
                "evidence_readiness_score": 85,
                "critical_blockers_count": 6,
            }
        ]
    }
    rerun = {
        "matches": [
            {
                "match_id": "match-1",
                "status": "SUCCESS",
                "final_decision_class": "BET_CANDIDATE_PREVIEW",
                "promotion_allowed": True,
                "evidence_readiness_score": 92,
                "critical_blockers_count": 1,
            }
        ]
    }

    result = compute_portfolio_delta(base, rerun, missing_fields_filled_total=27)

    assert result.candidate_count_delta == 1
    assert result.average_readiness_delta == 7
    assert result.matches_upgraded == ["match-1"]
    assert result.promotion_unlocked_matches == ["match-1"]
    assert result.blockers_removed_total == 5
    assert result.staking_logic_enabled is False
    assert result.roi_logic_enabled is False
