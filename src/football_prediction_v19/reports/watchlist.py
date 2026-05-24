# -*- coding: utf-8 -*-
"""Priority Watchlist formatter.

REPORT INTERPRETATION LAYER ONLY.
- Does not modify recommendations, probabilities, or tier logic.
- No betting, ROI, or staking logic.

Public API
----------
format_watchlist(predictions: list[dict]) -> str
    Returns a formatted watchlist string with Priority and No-Go sections.

append_watchlist_to_report(report_path: str, predictions: list[dict]) -> None
    Appends formatted watchlist to an existing report file (creates if needed).
    Silently skips if report_path is None/empty or predictions is empty.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["format_watchlist", "append_watchlist_to_report"]

_PRIORITY_TIERS = {"A_TIER", "B_TIER"}
_NO_GO_TIERS = {"HARD_NO_GO"}


def _format_priority_line(pred: dict) -> str:
    tier = pred.get("market_tier", "")
    score = pred.get("market_tier_score", 0)
    home = pred.get("home_team", pred.get("home", "?"))
    away = pred.get("away_team", pred.get("away", "?"))
    subtype = pred.get("recommended_market_subtype", "")
    reason = pred.get("market_tier_reason", "")
    return f"[{tier} | {score}] {home} vs {away} — {subtype} ({reason})"


def _format_nogo_line(pred: dict) -> str:
    home = pred.get("home_team", pred.get("home", "?"))
    away = pred.get("away_team", pred.get("away", "?"))
    subtype = pred.get("recommended_market_subtype", "")
    reason = pred.get("market_tier_reason", "")
    return f"[NO-GO] {home} vs {away} — {subtype} ({reason})"


def format_watchlist(predictions: list[dict]) -> str:
    """Format Priority Watchlist and No-Go Liste as a string.

    Parameters
    ----------
    predictions:
        List of recommendation dicts (output of build_market_tier).

    Returns
    -------
    str
        Formatted watchlist with two sections separated by a line.
    """
    priority = [p for p in predictions if p.get("market_tier") in _PRIORITY_TIERS]
    priority.sort(key=lambda p: p.get("market_tier_score", 0), reverse=True)

    nogo = [p for p in predictions if p.get("market_tier") in _NO_GO_TIERS]
    nogo.sort(key=lambda p: p.get("market_tier_score", 0))

    lines: list[str] = []

    lines.append("=== PRIORITY WATCHLIST ===")
    if priority:
        for pred in priority:
            lines.append(_format_priority_line(pred))
    else:
        lines.append("[keine Einträge]")

    lines.append("-" * 40)

    lines.append("=== NO-GO LISTE ===")
    if nogo:
        for pred in nogo:
            lines.append(_format_nogo_line(pred))
    else:
        lines.append("[keine Einträge]")

    return "\n".join(lines)


def append_watchlist_to_report(
    report_path: "str | None",
    predictions: list[dict],
) -> None:
    """Append formatted watchlist to report file (create if not exists).

    Parameters
    ----------
    report_path:
        Path to the report file.  Silently skipped if None or empty.
    predictions:
        List of recommendation dicts.  Silently skipped if empty.
    """
    if not report_path or not predictions:
        return

    content = "\n\n" + format_watchlist(predictions) + "\n"

    path = Path(report_path)
    if path.exists():
        with path.open("a", encoding="utf-8") as fh:
            fh.write(content)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.lstrip("\n"), encoding="utf-8")
