# -*- coding: utf-8 -*-
"""Shared Priority Watchlist utility for daily probability report scripts.

Prints two sections at the end of every daily report:

  PRIORITY WATCHLIST   — A_TIER / B_TIER rows, sorted by score desc then strength
  NO-GO LIST           — HARD_NO_GO and SUPPRESSED+warning rows

Rules
-----
- Watchlist: market_tier in {A_TIER, B_TIER}; exclude HARD_NO_GO
- La Liga exclusion: additionally drop rows whose recommended_market_subtype
  is BTTS or BOTH_OVER25_BTTS (poor walk-forward evidence in that league)
- No-Go List: market_tier == HARD_NO_GO OR
  (league_adjusted_strength == SUPPRESSED AND league_warning_flags != "")
- Sort: market_tier_score DESC, then league_adjusted_strength (HIGH > MEDIUM > LOW)
- Diagnostic only — no wagering, staking, ROI, or value language

This module is imported by every daily report script; it must not import
anything from outside the standard library or the project's own src package.
"""
from __future__ import annotations

from typing import Any

# Subtypes excluded from the watchlist specifically for La Liga
_LA_LIGA_EXCLUDED_SUBTYPES: frozenset[str] = frozenset({"BTTS", "BOTH_OVER25_BTTS"})

# Tier display order for the watchlist header
_WATCHLIST_TIERS: tuple[str, ...] = ("A_TIER", "B_TIER")

# Strength sort order (lower index = higher priority)
_STRENGTH_ORDER: dict[str, int] = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "SUPPRESSED": 3}


def _tier_score(rec: dict[str, Any]) -> int:
    """Return market_tier_score as int (0 if missing/invalid)."""
    try:
        return int(rec.get("market_tier_score", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _strength_rank(rec: dict[str, Any]) -> int:
    """Return sort key for league_adjusted_strength (lower = better)."""
    s = str(rec.get("league_adjusted_strength", "LOW")).upper()
    return _STRENGTH_ORDER.get(s, 99)


def _is_la_liga(league: str) -> bool:
    return "la liga" in str(league).lower()


def _watchlist_rows(results: list[dict], league: str) -> list[dict]:
    """Return rows eligible for the Priority Watchlist, sorted."""
    rows = []
    for r in results:
        rec   = r.get("recommended_market", {})
        tier  = str(rec.get("market_tier", ""))
        sub   = str(rec.get("recommended_market_subtype", "")).upper()
        if tier not in _WATCHLIST_TIERS:
            continue
        if _is_la_liga(league) and sub in _LA_LIGA_EXCLUDED_SUBTYPES:
            continue
        rows.append(r)
    rows.sort(
        key=lambda r: (
            -_tier_score(r["recommended_market"]),
            _strength_rank(r["recommended_market"]),
        )
    )
    return rows


def _nogo_rows(results: list[dict]) -> list[dict]:
    """Return HARD_NO_GO and SUPPRESSED+warning rows."""
    rows = []
    for r in results:
        rec      = r.get("recommended_market", {})
        tier     = str(rec.get("market_tier", ""))
        strength = str(rec.get("league_adjusted_strength", "")).upper()
        warning  = str(rec.get("league_warning_flags", "")).strip()
        if tier == "HARD_NO_GO":
            rows.append(r)
        elif strength == "SUPPRESSED" and warning:
            rows.append(r)
    return rows


def print_priority_watchlist(results: list[dict], league: str, sep: str = "=" * 72) -> None:
    """Print the Priority Watchlist and No-Go List sections to stdout.

    Parameters
    ----------
    results:
        List of per-fixture result dicts. Each must contain a
        ``"recommended_market"`` key holding the fully enriched dict
        (after apply_league_market_profile + build_market_tier).
    league:
        League name string used for La Liga-specific exclusion logic.
    sep:
        Separator line string used by the calling script.
    """
    sep2 = "-" * len(sep)

    # ------------------------------------------------------------------
    # Priority Watchlist
    # ------------------------------------------------------------------
    watchlist = _watchlist_rows(results, league)

    print()
    print(sep)
    print("  PRIORITY WATCHLIST  [diagnostic only — no wagering claims]")
    print(sep)

    if not watchlist:
        print("  (No A_TIER or B_TIER recommendations for today.)")
    else:
        print(
            f"  {'#':<3} {'Match':<35} {'Tier':<11} {'Score':>5}  "
            f"{'AdjStr':<11} {'Subtype':<22} {'Read'}"
        )
        print(sep2)
        for idx, r in enumerate(watchlist, 1):
            rec   = r["recommended_market"]
            game  = f"{r['home'][:16]} vs {r['away'][:16]}"
            tier  = rec.get("market_tier", "")
            score = _tier_score(rec)
            adj   = rec.get("league_adjusted_strength", "")
            sub   = rec.get("recommended_market_subtype", "NONE")
            read  = rec.get("recommended_market_read", "")[:28]
            print(
                f"  {idx:<3} {game:<35} {tier:<11} {score:>5}  "
                f"{adj:<11} {sub:<22} {read}"
            )
        print()
        print(
            f"  {len(watchlist)} match(es) on Priority Watchlist. "
            "Diagnostic classification only."
        )

    # ------------------------------------------------------------------
    # No-Go List
    # ------------------------------------------------------------------
    nogo = _nogo_rows(results)

    print()
    print(sep)
    print("  NO-GO LIST  [diagnostic only — markets flagged as unreliable]")
    print(sep)

    if not nogo:
        print("  (No HARD_NO_GO or SUPPRESSED+warning recommendations today.)")
    else:
        print(
            f"  {'#':<3} {'Match':<35} {'Tier':<11} {'Score':>5}  "
            f"{'AdjStr':<11} {'Subtype':<22} {'Reason'}"
        )
        print(sep2)
        for idx, r in enumerate(nogo, 1):
            rec    = r["recommended_market"]
            game   = f"{r['home'][:16]} vs {r['away'][:16]}"
            tier   = rec.get("market_tier", "")
            score  = _tier_score(rec)
            adj    = rec.get("league_adjusted_strength", "")
            sub    = rec.get("recommended_market_subtype", "NONE")
            flags  = rec.get("market_tier_flags", "") or rec.get("league_warning_flags", "")
            reason = str(flags)[:40] if flags else rec.get("market_tier_reason", "")[:40]
            print(
                f"  {idx:<3} {game:<35} {tier:<11} {score:>5}  "
                f"{adj:<11} {sub:<22} {reason}"
            )
        print()
        print(
            f"  {len(nogo)} match(es) flagged. "
            "These subtypes have poor walk-forward evidence in this league context."
        )

    print()
