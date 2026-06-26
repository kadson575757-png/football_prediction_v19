# -*- coding: utf-8 -*-
"""Portfolio summary renderer for v1.9 batch workbench preview."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_portfolio_summary(matches: list[dict[str, object]], output_path: str | Path) -> dict[str, object]:
    success = [m for m in matches if m.get("status") == "SUCCESS"]
    classes = [str(m.get("final_decision_class", "")) for m in success]
    readiness = [int(m.get("evidence_readiness_score", 0) or 0) for m in success]
    summary = {
        "matches_total": len(matches),
        "analyst_lean_only_count": classes.count("ANALYST_LEAN_ONLY"),
        "no_bet_count": classes.count("NO_BET_RECOMMENDED"),
        "bet_candidate_preview_count": classes.count("BET_CANDIDATE_PREVIEW"),
        "strong_bet_candidate_preview_count": classes.count("STRONG_BET_CANDIDATE_PREVIEW"),
        "conflict_review_count": classes.count("CONFLICT_REVIEW"),
        "average_readiness_score": round(sum(readiness) / len(readiness), 2) if readiness else 0,
        "high_conflict_count": len([m for m in success if str(m.get("conflict_score", "")) == "HIGH"]),
        "critical_blockers_total": sum(int(m.get("critical_blockers_count", 0) or 0) for m in success),
        "promotion_allowed_count": len([m for m in success if bool(m.get("promotion_allowed", False))]),
        "strong_promotion_allowed_count": len([m for m in success if bool(m.get("strong_promotion_allowed", False))]),
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(summary), encoding="utf-8")
    return summary


def _render(summary: dict[str, object]) -> str:
    rows = pd.DataFrame([summary])
    return "\n".join([
        "# v1.9 Portfolio Summary Preview",
        "",
        _table(rows),
        "",
        "Preview only. No production betting, no stake, no ROI.",
        "",
    ])


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)
