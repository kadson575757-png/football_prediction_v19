# -*- coding: utf-8 -*-
"""Shared context signal helpers for Phase-9 daily report integration.

Provides:
  - get_team_context_features   -- last-row lookup for a team in enriched history
  - get_fixture_context_features -- combine home + away context for a fixture
  - print_context_signals_section -- print CONTEXT SIGNALS block for A/B TIER matches
  - compute_context_signal_analysis -- evaluator summary lines for context signals
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Allow imports from src when this module is used by the scripts
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def get_team_context_features(team: str, history_df: pd.DataFrame) -> dict[str, Any]:
    """Return the most-recent row's feature values for *team*.

    Searches both home_team and away_team columns, returns the last-dated row.
    If history_df has no matches for the team, returns an empty dict.
    """
    mask = (history_df["home_team"] == team) | (history_df["away_team"] == team)
    team_games = history_df[mask].sort_values("date").tail(1)
    if team_games.empty:
        return {}
    return team_games.iloc[0].to_dict()


def get_fixture_context_features(
    home: str,
    away: str,
    match_date: Any,
    history_df: pd.DataFrame,
) -> dict[str, Any]:
    """Build a context feature dict for an upcoming fixture.

    Combines home- and away-team lookups from enriched *history_df*.
    Derby flags are computed directly from the team pair via
    ``compute_rivalry_features``.

    All values default to ``""`` when the corresponding column is absent.
    """
    h_feats = get_team_context_features(home, history_df)
    a_feats = get_team_context_features(away, history_df)

    ctx: dict[str, Any] = {}

    # ---- H2H features (from most-recent H2H match in history) ----
    h2h_mask = (
        ((history_df["home_team"] == home) & (history_df["away_team"] == away)) |
        ((history_df["home_team"] == away) & (history_df["away_team"] == home))
    )
    h2h_row = history_df[h2h_mask].sort_values("date").tail(1)
    for col in ("h2h_btts_rate", "h2h_avg_goals", "h2h_n"):
        if not h2h_row.empty and col in h2h_row.columns:
            ctx[col] = h2h_row.iloc[0][col]
        else:
            ctx[col] = ""

    # ---- Elo ----
    ctx["elo_home"] = h_feats.get("elo_home", "")
    ctx["elo_away"] = a_feats.get("elo_away", "")
    elo_h = ctx["elo_home"]
    elo_a = ctx["elo_away"]
    if elo_h != "" and elo_a != "" and elo_h is not None and elo_a is not None:
        try:
            ctx["elo_diff"] = float(elo_h) - float(elo_a)
        except (TypeError, ValueError):
            ctx["elo_diff"] = h_feats.get("elo_diff", "")
    else:
        ctx["elo_diff"] = h_feats.get("elo_diff", "")

    # ---- Referee features (from home team's last row; fallback to away) ----
    for col in ("ref_btts_rate", "ref_avg_goals", "ref_over25_rate", "ref_n"):
        val = h_feats.get(col)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            val = a_feats.get(col, "")
        ctx[col] = "" if val is None else val

    # ---- Fatigue / rest ----
    ctx["home_days_since_last"] = h_feats.get("home_days_since_last", "")
    ctx["away_days_since_last"] = a_feats.get("away_days_since_last", "")
    ctx["home_short_rest"] = int(bool(h_feats.get("home_short_rest", 0))) if h_feats else ""
    ctx["away_short_rest"] = int(bool(a_feats.get("away_short_rest", 0))) if a_feats else ""
    ctx["home_games_last_30_days"] = h_feats.get("home_games_last_30_days", "")
    ctx["away_games_last_30_days"] = a_feats.get("away_games_last_30_days", "")

    # ---- Table context ----
    ctx["home_table_rank"] = h_feats.get("home_table_rank", "")
    ctx["away_table_rank"] = a_feats.get("away_table_rank", "")
    ctx["rank_diff"]       = h_feats.get("rank_diff", "")
    ctx["dead_rubber_flag"]      = int(bool(h_feats.get("dead_rubber_flag", 0)))      if h_feats else ""
    ctx["home_relegation_zone"]  = int(bool(h_feats.get("home_relegation_zone", 0)))  if h_feats else ""
    ctx["away_relegation_zone"]  = int(bool(a_feats.get("away_relegation_zone", 0)))  if a_feats else ""
    ctx["home_title_race"]       = int(bool(h_feats.get("home_title_race", 0)))       if h_feats else ""
    ctx["away_title_race"]       = int(bool(a_feats.get("away_title_race", 0)))       if a_feats else ""

    # ---- Derby / rivalry (computed fresh for this fixture pair) ----
    try:
        from football_prediction_v19.context_features import compute_rivalry_features
        derby_df = pd.DataFrame([{
            "date":       pd.Timestamp(match_date),
            "home_team":  home,
            "away_team":  away,
            "home_goals": 0,
            "away_goals": 0,
        }])
        derby_result = compute_rivalry_features(derby_df)
        ctx["is_derby"]   = int(bool(derby_result["is_derby"].iloc[0]))
        ctx["derby_name"] = str(derby_result["derby_name"].iloc[0])
    except Exception:
        ctx["is_derby"]   = ""
        ctx["derby_name"] = ""

    return ctx


# ---------------------------------------------------------------------------
# Context-column additions for _csv_rows
# ---------------------------------------------------------------------------

CONTEXT_CSV_KEYS: tuple[str, ...] = (
    "h2h_btts_rate",
    "elo_diff",
    "ref_btts_rate",
    "ref_avg_goals",
    "home_days_since_last",
    "away_days_since_last",
    "home_short_rest",
    "away_short_rest",
    "is_derby",
    "derby_name",
    "dead_rubber_flag",
    "home_table_rank",
    "away_table_rank",
    "rank_diff",
)


def context_csv_fields(ctx: dict[str, Any]) -> dict[str, Any]:
    """Return only the CSV-relevant context fields from *ctx*."""
    return {k: ctx.get(k, "") for k in CONTEXT_CSV_KEYS}


# ---------------------------------------------------------------------------
# CONTEXT SIGNALS printer
# ---------------------------------------------------------------------------

def _fmt(val: Any, fmt: str | None = None) -> str:
    """Format *val* gracefully; NaN / None / '' → '—'."""
    if val is None or val == "":
        return "—"
    if isinstance(val, float) and np.isnan(val):
        return "—"
    if fmt:
        try:
            return fmt.format(float(val))
        except (TypeError, ValueError):
            return "—"
    return str(val)


def print_context_signals_section(
    results: list[dict[str, Any]],
    sep: str = "=" * 72,
) -> None:
    """Print the CONTEXT SIGNALS section for A_TIER and B_TIER matches only.

    If no A/B_TIER match is in *results*, the section is omitted entirely.
    """
    priority = [
        r for r in results
        if r.get("recommended_market", {}).get("market_tier", "") in ("A_TIER", "B_TIER")
    ]
    if not priority:
        return

    print()
    print(sep)
    print("  CONTEXT SIGNALS  (A_TIER / B_TIER matches only)")
    print(sep)

    for r in priority:
        ctx  = r.get("ctx", {})
        home = r["home"]
        away = r["away"]
        tier = r.get("recommended_market", {}).get("market_tier", "")

        print(f"\n  {home} vs {away}  [{tier}]")
        print(f"  {'─' * 60}")

        # H2H BTTS
        h2h_btts = _fmt(ctx.get("h2h_btts_rate"), "{:.2f}")
        h2h_n    = _fmt(ctx.get("h2h_n"))
        print(f"    H2H BTTS Rate:     {h2h_btts}  ({h2h_n} Spiele)")

        # Elo diff
        elo_diff = ctx.get("elo_diff", "")
        if elo_diff != "" and elo_diff is not None:
            try:
                sign = "+" if float(elo_diff) >= 0 else ""
                print(f"    Elo Diff:          {sign}{float(elo_diff):.0f}")
            except (TypeError, ValueError):
                print("    Elo Diff:          —")
        else:
            print("    Elo Diff:          —")

        # Referee
        ref_btts  = _fmt(ctx.get("ref_btts_rate"),  "{:.1%}")
        ref_goals = _fmt(ctx.get("ref_avg_goals"),   "{:.1f}")
        print(f"    Schiedsrichter:    BTTS {ref_btts}, {ref_goals} Tore/Spiel")

        # Fatigue
        h_rest = ctx.get("home_short_rest", "")
        a_rest = ctx.get("away_short_rest", "")
        h_days = _fmt(ctx.get("home_days_since_last"))
        a_days = _fmt(ctx.get("away_days_since_last"))
        if h_rest == 1 and a_rest != 1:
            fatigue_str = f"Home SHORT REST ({h_days} Tage)"
        elif a_rest == 1 and h_rest != 1:
            fatigue_str = f"Away SHORT REST ({a_days} Tage)"
        elif h_rest == 1 and a_rest == 1:
            fatigue_str = "BOTH SHORT REST"
        else:
            fatigue_str = "Kein Kurzpause-Problem"
        print(f"    Fatigue:           {fatigue_str}")

        # Derby
        is_derby   = ctx.get("is_derby", "")
        derby_name = ctx.get("derby_name", "")
        derby_str  = "Ja" if is_derby == 1 else "Nein"
        if is_derby == 1 and derby_name:
            derby_str += f" — {derby_name}"
        print(f"    Derby:             {derby_str}")

        # Dead Rubber
        dr = ctx.get("dead_rubber_flag", "")
        print(f"    Dead Rubber:       {'Ja' if dr == 1 else 'Nein'}")

        # Table rank
        h_rank = _fmt(ctx.get("home_table_rank"))
        a_rank = _fmt(ctx.get("away_table_rank"))
        print(f"    Tabellenrang:      Home #{h_rank} vs Away #{a_rank}")

    print()
    print(sep)


# ---------------------------------------------------------------------------
# Context signal analysis for evaluate_daily_recommendations.py
# ---------------------------------------------------------------------------

def compute_context_signal_analysis(df: pd.DataFrame) -> list[str]:
    """Return summary lines for the CONTEXT SIGNAL ANALYSIS section.

    *df* is the merged evaluation DataFrame that has both pre-match columns
    (including optional context columns) and actual-result columns.
    Gracefully handles missing context columns.
    """
    lines: list[str] = ["## Context Signal Analysis", ""]

    # Determine success column
    success_col: str | None = None
    for col in ("type_success", "subtype_success"):
        if col in df.columns and df[col].notna().any():
            success_col = col
            break

    if success_col is None:
        lines.append("  (No success column available for context analysis)")
        lines.append("")
        return lines

    def _hit_rate(mask: pd.Series) -> tuple[int, float]:
        sub = df[mask & df[success_col].notna()]
        n   = len(sub)
        rate = float(sub[success_col].sum()) / n if n else 0.0
        return n, rate

    def _truthy_mask(col: str) -> pd.Series:
        return df[col].astype(str).str.strip().isin(["1", "1.0", "True", "true"])

    # Derby
    if "is_derby" in df.columns:
        n, rate = _hit_rate(_truthy_mask("is_derby"))
        lines += [f"Derby Matches:", f"  n={n}, Hit Rate: {rate:.1%}", ""]

    # Short Rest (Away)
    if "away_short_rest" in df.columns:
        n, rate = _hit_rate(_truthy_mask("away_short_rest"))
        lines += [f"Short Rest (Away):", f"  n={n}, Hit Rate: {rate:.1%}", ""]

    # Dead Rubber
    if "dead_rubber_flag" in df.columns:
        n, rate = _hit_rate(_truthy_mask("dead_rubber_flag"))
        lines += [f"Dead Rubber:", f"  n={n}, Hit Rate: {rate:.1%}", ""]

    # High Elo Diff (>100)
    if "elo_diff" in df.columns:
        elo_num  = pd.to_numeric(df["elo_diff"], errors="coerce")
        elo_mask = elo_num.abs() > 100
        n, rate  = _hit_rate(elo_mask)
        lines += [f"High Elo Diff (>100):", f"  n={n}, Hit Rate: {rate:.1%}", ""]

    # High H2H BTTS Rate (>0.6)
    if "h2h_btts_rate" in df.columns:
        h2h_num  = pd.to_numeric(df["h2h_btts_rate"], errors="coerce")
        h2h_mask = h2h_num > 0.6
        n, rate  = _hit_rate(h2h_mask)
        lines += [f"High H2H BTTS Rate (>0.6):", f"  n={n}, Hit Rate: {rate:.1%}", ""]

    if len(lines) <= 2:
        lines.append("  (No context columns found in evaluation data)")
        lines.append("")

    return lines
