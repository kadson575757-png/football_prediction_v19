# -*- coding: utf-8 -*-
"""Batch-wide missing data priority board."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


PRIORITIES = [
    ("Recent Form", "home_recent_xg_for, away_recent_xg_for, home_recent_xg_against, away_recent_xg_against", "1X2 | Goals | Score Family", "BET_CANDIDATE_PREVIEW"),
    ("Big Chances", "home_big_chances_for, away_big_chances_for, home_big_chances_against, away_big_chances_against", "Goals | BTTS | Score Family", "BET_CANDIDATE_PREVIEW"),
    ("Availability", "goalkeeper, missing, suspended, doubtful players", "1X2 | DNB | BTTS", "BET_CANDIDATE_PREVIEW"),
    ("Opening/Closing Market", "home/draw/away open and closing odds", "1X2 | Double Chance", "BET_CANDIDATE_PREVIEW"),
    ("DNB/OU Market", "dnb_home_odds, dnb_away_odds, over_line, over_current_odds, under_current_odds", "DNB | Over/Under", "BET_CANDIDATE_PREVIEW"),
]


def build_missing_data_priority_board(matches: list[dict[str, object]], output_path: str | Path) -> list[dict[str, object]]:
    success_ids = [str(m.get("match_id", "")) for m in matches if m.get("status") == "SUCCESS"]
    rows = []
    for idx, (group, fields, markets, upgrade) in enumerate(PRIORITIES, start=1):
        rows.append({
            "priority_rank": idx,
            "field_group": group,
            "fields": fields,
            "affected_matches_count": len(success_ids),
            "affected_match_ids": ", ".join(success_ids),
            "unlocks_market_families": markets,
            "can_upgrade_to": upgrade,
            "reason": f"{group} is a critical blocker for promotion preview.",
        })
    Path(output_path).write_text("# v1.9 Missing Data Priority Board\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    return rows


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
