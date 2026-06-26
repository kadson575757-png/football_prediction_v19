# -*- coding: utf-8 -*-
"""Market family portfolio report for batch workbench preview."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

FAMILIES = ["1X2", "Double Chance", "DNB", "Over/Under", "BTTS", "Score Family", "No-Bet"]


def build_market_family_portfolio(matches: list[dict[str, object]], output_path: str | Path) -> list[dict[str, object]]:
    rows = []
    for family in FAMILIES:
        statuses = []
        for match in matches:
            statuses.append(str(match.get("market_family_statuses", {}).get(family, "")))
        rows.append({
            "market_family": family,
            "ready_count": statuses.count("READY"),
            "partial_count": statuses.count("PARTIAL"),
            "blocked_count": statuses.count("BLOCKED"),
            "no_bet_count": statuses.count("NO_BET"),
            "top_candidate_match": _top_candidate(matches),
            "common_blocker": _common_blocker(family),
            "next_data_needed": _next_data(family),
        })
    Path(output_path).write_text("# v1.9 Market Family Portfolio Preview\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    return rows


def _top_candidate(matches: list[dict[str, object]]) -> str:
    candidates = [m for m in matches if m.get("promotion_allowed")]
    return str(candidates[0].get("match_id", "")) if candidates else ""


def _common_blocker(family: str) -> str:
    return "safety priority" if family == "No-Bet" else "missing market/recent/availability data"


def _next_data(family: str) -> str:
    if family == "DNB":
        return "DNB odds"
    if family == "Over/Under":
        return "OU line, big chances, recent form"
    if family == "No-Bet":
        return "resolve critical blockers before any promotion review"
    return "recent form, availability and market movement"


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
