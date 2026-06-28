# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta


def evaluate_asof_guard(match_date: str, as_of_date: str | None = None, allow_post_match_analysis: bool = False) -> dict[str, object]:
    if not match_date:
        return {"as_of_date": "", "post_match_analysis": False, "leakage_warning": False, "asof_guard_status": "BLOCKED", "asof_guard_reason": "match_date missing"}
    match = _parse(match_date)
    if as_of_date:
        asof = _parse(as_of_date)
    else:
        asof = match - timedelta(days=1)
    post = asof >= match
    if post and not allow_post_match_analysis:
        status = "BLOCKED"
        reason = "as_of_date must be before match_date for pre-match analysis"
    elif post:
        status = "WARNING"
        reason = "post-match analysis allowed explicitly; not a pre-match prediction"
    else:
        status = "CLEAN"
        reason = "as_of_date is before match_date"
    return {
        "as_of_date": asof.isoformat(),
        "post_match_analysis": bool(post),
        "leakage_warning": bool(post),
        "asof_guard_status": status,
        "asof_guard_reason": reason,
    }


def _parse(value: str) -> date:
    return datetime.strptime(str(value), "%Y-%m-%d").date()
