# -*- coding: utf-8 -*-
"""No-bet/blocker review for batch workbench preview."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


GROUPS = [
    ("Missing Recent Form", "missing recent form", "HIGH", "1X2 / Goals / Score", "Fill recent form fields"),
    ("Missing Big Chances", "missing big chances", "HIGH", "Goals / BTTS / Score", "Fill big chances fields"),
    ("Missing Availability", "missing full availability details", "HIGH", "1X2 / DNB / BTTS", "Fill goalkeeper and absences"),
    ("Missing Market Movement", "missing opening/closing odds", "HIGH", "1X2 / DNB / OU", "Fill opening/closing odds"),
    ("High Conflict", "conflict score HIGH", "HIGH", "All", "Resolve contradictory evidence"),
    ("Safety Disabled Productive Betting", "productive betting safety disabled", "HIGH", "All", "Safety remains disabled by design"),
    ("No-Bet Recommended", "NO_BET_RECOMMENDED", "HIGH", "All", "Review no-bet reason"),
    ("Conflict Review", "CONFLICT_REVIEW", "HIGH", "All", "Manual conflict review"),
]


def build_batch_no_bet_review(matches: list[dict[str, object]], output_path: str | Path) -> list[dict[str, object]]:
    rows = []
    for match in matches:
        if match.get("status") != "SUCCESS":
            continue
        blockers = str(match.get("critical_blockers", "")).lower()
        final_class = str(match.get("final_decision_class", ""))
        for group, token, severity, markets, action in GROUPS:
            if token.lower() in blockers or token == final_class or (group == "High Conflict" and match.get("conflict_score") == "HIGH"):
                rows.append({"group": group, "match_id": match.get("match_id", ""), "blocker": token, "severity": severity, "affected markets": markets, "next action": action})
    Path(output_path).write_text("# v1.9 Batch No-Bet Review Preview\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    return rows


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
