# -*- coding: utf-8 -*-
"""Portfolio before/after delta preview for v1.9 batch workflows."""
from __future__ import annotations

from dataclasses import dataclass


V19_PORTFOLIO_DELTA_PREVIEW_READY = "V19_PORTFOLIO_DELTA_PREVIEW_READY"


@dataclass(frozen=True)
class V19PortfolioDeltaResult:
    portfolio_delta_status: str
    base_matches_total: int
    rerun_matches_total: int
    base_candidate_count: int
    rerun_candidate_count: int
    candidate_count_delta: int
    base_strong_candidate_count: int
    rerun_strong_candidate_count: int
    strong_candidate_count_delta: int
    base_no_bet_count: int
    rerun_no_bet_count: int
    no_bet_count_delta: int
    base_analyst_lean_count: int
    rerun_analyst_lean_count: int
    analyst_lean_count_delta: int
    base_conflict_review_count: int
    rerun_conflict_review_count: int
    conflict_review_count_delta: int
    average_readiness_before: float
    average_readiness_after: float
    average_readiness_delta: float
    matches_upgraded: list[str]
    matches_downgraded: list[str]
    matches_unchanged: list[str]
    blockers_removed_total: int
    blockers_remaining_total: int
    missing_fields_filled_total: int
    promotion_unlocked_matches: list[str]
    promotion_lost_matches: list[str]
    final_summary: str
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


def compute_portfolio_delta(base: dict[str, object], rerun: dict[str, object], *, missing_fields_filled_total: int = 0) -> V19PortfolioDeltaResult:
    base_matches = _matches(base)
    rerun_matches = _matches(rerun)
    base_by_id = {str(m.get("match_id", "")): m for m in base_matches}
    rerun_by_id = {str(m.get("match_id", "")): m for m in rerun_matches}
    upgraded: list[str] = []
    downgraded: list[str] = []
    unchanged: list[str] = []
    promotion_unlocked: list[str] = []
    promotion_lost: list[str] = []
    for match_id, before in base_by_id.items():
        after = rerun_by_id.get(match_id, before)
        before_rank = _class_rank(str(before.get("final_decision_class", "")))
        after_rank = _class_rank(str(after.get("final_decision_class", "")))
        if after_rank > before_rank:
            upgraded.append(match_id)
        elif after_rank < before_rank:
            downgraded.append(match_id)
        else:
            unchanged.append(match_id)
        if not _bool(before.get("promotion_allowed", False)) and _bool(after.get("promotion_allowed", False)):
            promotion_unlocked.append(match_id)
        if _bool(before.get("promotion_allowed", False)) and not _bool(after.get("promotion_allowed", False)):
            promotion_lost.append(match_id)
    before_avg = _avg_readiness(base_matches)
    after_avg = _avg_readiness(rerun_matches)
    candidate_delta = _count_classes(rerun_matches, {"BET_CANDIDATE_PREVIEW"}) - _count_classes(base_matches, {"BET_CANDIDATE_PREVIEW"})
    summary = "No filled values; portfolio unchanged." if missing_fields_filled_total == 0 and not upgraded and not downgraded else "Portfolio changed after filled completion values."
    blockers_remaining = sum(int(m.get("critical_blockers_count", 0) or 0) for m in rerun_matches)
    blockers_removed = max(0, sum(int(m.get("critical_blockers_count", 0) or 0) for m in base_matches) - blockers_remaining)
    return V19PortfolioDeltaResult(
        V19_PORTFOLIO_DELTA_PREVIEW_READY,
        len(base_matches),
        len(rerun_matches),
        _count_classes(base_matches, {"BET_CANDIDATE_PREVIEW"}),
        _count_classes(rerun_matches, {"BET_CANDIDATE_PREVIEW"}),
        candidate_delta,
        _count_classes(base_matches, {"STRONG_BET_CANDIDATE_PREVIEW"}),
        _count_classes(rerun_matches, {"STRONG_BET_CANDIDATE_PREVIEW"}),
        _count_classes(rerun_matches, {"STRONG_BET_CANDIDATE_PREVIEW"}) - _count_classes(base_matches, {"STRONG_BET_CANDIDATE_PREVIEW"}),
        _count_classes(base_matches, {"NO_BET_RECOMMENDED"}),
        _count_classes(rerun_matches, {"NO_BET_RECOMMENDED"}),
        _count_classes(rerun_matches, {"NO_BET_RECOMMENDED"}) - _count_classes(base_matches, {"NO_BET_RECOMMENDED"}),
        _count_classes(base_matches, {"ANALYST_LEAN_ONLY"}),
        _count_classes(rerun_matches, {"ANALYST_LEAN_ONLY"}),
        _count_classes(rerun_matches, {"ANALYST_LEAN_ONLY"}) - _count_classes(base_matches, {"ANALYST_LEAN_ONLY"}),
        _count_classes(base_matches, {"CONFLICT_REVIEW"}),
        _count_classes(rerun_matches, {"CONFLICT_REVIEW"}),
        _count_classes(rerun_matches, {"CONFLICT_REVIEW"}) - _count_classes(base_matches, {"CONFLICT_REVIEW"}),
        before_avg,
        after_avg,
        round(after_avg - before_avg, 2),
        upgraded,
        downgraded,
        unchanged,
        blockers_removed,
        blockers_remaining,
        missing_fields_filled_total,
        promotion_unlocked,
        promotion_lost,
        summary,
        False,
        False,
        False,
        False,
    )


def _matches(payload: dict[str, object]) -> list[dict[str, object]]:
    return [m for m in payload.get("matches", []) if isinstance(m, dict) and m.get("status", "SUCCESS") == "SUCCESS"]


def _count_classes(matches: list[dict[str, object]], classes: set[str]) -> int:
    return len([m for m in matches if str(m.get("final_decision_class", "")) in classes])


def _avg_readiness(matches: list[dict[str, object]]) -> float:
    if not matches:
        return 0
    return round(sum(float(m.get("evidence_readiness_score", 0) or 0) for m in matches) / len(matches), 2)


def _class_rank(value: str) -> int:
    return {
        "BLOCKED_MISSING_DATA": 0,
        "CONFLICT_REVIEW": 1,
        "NO_BET_RECOMMENDED": 1,
        "ANALYST_LEAN_ONLY": 2,
        "BET_CANDIDATE_PREVIEW": 3,
        "STRONG_BET_CANDIDATE_PREVIEW": 4,
    }.get(value, 0)


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}
