# -*- coding: utf-8 -*-
"""Candidate shortlist preview for batch workbench."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ORDER = {
    "STRONG_BET_CANDIDATE_PREVIEW": 1,
    "BET_CANDIDATE_PREVIEW": 2,
    "ANALYST_LEAN_ONLY": 3,
    "NO_BET_RECOMMENDED": 4,
    "CONFLICT_REVIEW": 5,
    "BLOCKED_MISSING_DATA": 6,
}


def build_candidate_shortlist(matches: list[dict[str, object]], output_path: str | Path) -> list[dict[str, object]]:
    rows = []
    for match in sorted([m for m in matches if m.get("status") == "SUCCESS"], key=lambda m: (ORDER.get(str(m.get("final_decision_class", "")), 99), -int(m.get("evidence_readiness_score", 0) or 0))):
        final_class = str(match.get("final_decision_class", ""))
        final_action = "Fill critical missing data before promotion." if final_class == "ANALYST_LEAN_ONLY" else "Preview candidate only; no stake or ROI." if "CANDIDATE" in final_class else "No production action."
        rows.append({
            "rank": len(rows) + 1,
            "match_id": match.get("match_id", ""),
            "match": f"{match.get('home_team', '')} vs {match.get('away_team', '')}",
            "final_decision_class": final_class,
            "readiness_score": match.get("evidence_readiness_score", 0),
            "conflict_score": match.get("conflict_score", ""),
            "promotion_allowed": match.get("promotion_allowed", False),
            "strongest_lean": match.get("strongest_analyst_lean", ""),
            "candidate_reason": match.get("decision_explanation", "Preview-only ranking."),
            "blocker_summary": match.get("critical_blockers", ""),
            "final_action": final_action,
        })
    Path(output_path).write_text("# v1.9 Candidate Shortlist Preview\n\n" + _table(pd.DataFrame(rows)) + "\n\nNo stakes. No ROI. No automatic betting.\n", encoding="utf-8")
    return rows


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
