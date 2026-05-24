# -*- coding: utf-8 -*-
"""Aggregate ALL walk-forward season replay evaluation CSVs.

Reads every *_evaluation.csv from outputs/season_replay/, combines them, and
writes:
  outputs/season_replay/walk_forward_aggregate_summary.md
  outputs/season_replay/walk_forward_aggregate_summary.csv

Diagnostic only. No betting rules. No ROI.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

ROOT    = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "season_replay"

# ---------------------------------------------------------------------------
# League display ordering
# ---------------------------------------------------------------------------
LEAGUE_ORDER = [
    "Premier League", "La Liga", "Serie A", "Ligue 1",
    "Eredivisie", "2. Bundesliga",
]

SUBTYPE_ORDER = [
    "UNDER_35", "UNDER_25",
    "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2",
    "DIRECTION_HOME", "DIRECTION_AWAY",
    "AVOID_VOLATILE", "AVOID_LOW_CONTROL",
    "OVER_25", "BTTS", "BOTH_OVER25_BTTS",
    "OBSERVE_DATA_WARNING", "NONE",
]

TYPE_ORDER = ["UNDER", "DOUBLE_CHANCE", "AVOID", "DIRECTION", "BTTS_OVER", "OBSERVE_ONLY"]

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_all() -> pd.DataFrame:
    files = sorted(OUT_DIR.glob("*_evaluation.csv"))
    if not files:
        print(f"ERROR: No *_evaluation.csv files found in {OUT_DIR}", file=sys.stderr)
        sys.exit(1)

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df["_source"] = f.stem
        dfs.append(df)
        league  = df["league"].iloc[0]  if "league"  in df.columns else "?"
        season  = df["season"].iloc[0]  if "season"  in df.columns else "?"
        ev_n    = df["type_success"].notna().sum() if "type_success" in df.columns else 0
        print(f"  {f.name:45s}  {len(df):3d} rows  {ev_n:3d} evaluatable  [{league} {season}]")

    combined = pd.concat(dfs, ignore_index=True)

    # Coerce success cols to float
    for col in ("type_success", "subtype_success"):
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Coerce actual goals cols
    for col in ("actual_total_goals", "actual_home_goals", "actual_away_goals",
                "actual_over25", "actual_under25", "actual_under35", "actual_btts"):
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Normalise league names
    league_clean = {
        "Premier League": "Premier League",
        "EPL": "Premier League",
        "La Liga": "La Liga",
        "Serie A": "Serie A",
        "Ligue 1": "Ligue 1",
        "Eredivisie": "Eredivisie",
        "2. Bundesliga": "2. Bundesliga",
        "Bundesliga": "Bundesliga",
    }
    if "league" in combined.columns:
        combined["league"] = combined["league"].map(lambda x: league_clean.get(str(x).strip(), str(x).strip()))

    print(f"\n  Total rows loaded : {len(combined)}")
    return combined

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hits_n(series: pd.Series) -> tuple[int, int]:
    s = series.dropna()
    return int(s.sum()), len(s)

def _rate(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.mean()) if len(s) > 0 else float("nan")

def _warn(n: int, thresh: int = 20) -> str:
    return "  ⚠ n<20" if n < thresh else ""

def _row_line(label: str, n: int, hits: int, lw: int = 30, thresh: int = 20) -> str:
    rate = hits / n if n > 0 else float("nan")
    w    = _warn(n, thresh)
    rate_s = f"{rate:>7.1%}" if not math.isnan(rate) else "    n/a"
    return f"  {label:<{lw}} {n:>5} {hits:>5} {rate_s}{w}"

def _section(title: str) -> list[str]:
    return [f"## {title}", ""]

def _divider(width: int = 70) -> str:
    return "  " + "-" * width

# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _type_table(
    ev: pd.DataFrame,
    group_cols: list[str],
    col: str = "type_success",
    lw: int = 36,
    sort_col: str = "rate",
    min_n: int = 1,
) -> list[str]:
    lines = [f"  {'Group':<{lw}} {'n':>5} {'hits':>5} {'rate':>7}", _divider(lw + 25)]
    rows_out: list[tuple] = []
    for keys, grp in ev.groupby(group_cols):
        g = grp[grp[col].notna()]
        n = len(g)
        if n < min_n:
            continue
        hits = int(g[col].sum())
        rate = hits / n
        label = " | ".join(str(k) for k in (keys if isinstance(keys, tuple) else [keys]))
        rows_out.append((label, n, hits, rate))
    if sort_col == "rate":
        rows_out.sort(key=lambda x: -x[3])
    else:
        rows_out.sort(key=lambda x: x[0])
    for label, n, hits, rate in rows_out:
        lines.append(_row_line(label, n, hits, lw))
    lines.append("")
    return lines

# ---------------------------------------------------------------------------
# League-aware profile section builder  (sections 19-25)
# ---------------------------------------------------------------------------

_LP_COLS = {
    "league_adjusted_strength",
    "league_profile",
    "league_warning_flags",
    "league_preferred_subtype",
    "league_suppressed_subtype",
}
_GOAL_FRIENDLY_LEAGUES = {"Eredivisie", "2. Bundesliga"}
_A_TIER_SUBTYPES = {"UNDER_35", "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2"}
_CHAOS_SAFE = {"low (<4)", "medium (4-6)"}


def _build_lp_sections(
    df: pd.DataFrame,
    ev: pd.DataFrame,
    agg_rows: list[dict],
) -> list[str]:
    """Build sections 19-25: league-aware profile diagnostics.

    Gracefully handles CSVs that pre-date the league profile layer.
    No betting rules. No ROI. Diagnostics only.
    """
    lines: list[str] = []

    # ── 19. Coverage ────────────────────────────────────────────────────────
    lines += _section("19. League Profile Field Coverage")

    present_cols = _LP_COLS & set(df.columns)
    rows_with_lp = int(df["league_adjusted_strength"].notna().sum()) if "league_adjusted_strength" in df.columns else 0
    rows_total   = len(df)
    pct          = rows_with_lp / rows_total if rows_total else 0.0

    lines += [
        f"  Rows with league profile fields : {rows_with_lp:,} / {rows_total:,}  ({pct:.0%})",
        f"  Fields present                  : {', '.join(sorted(present_cols)) if present_cols else '— none —'}",
        "",
    ]

    # Identify which source files are missing LP fields
    missing_sources: list[str] = []
    if "league_adjusted_strength" in df.columns and "_source" in df.columns:
        for src, grp in df.groupby("_source"):
            if grp["league_adjusted_strength"].isna().all():
                missing_sources.append(str(src))

    if missing_sources:
        lines.append(
            "  ⚠ WARNING: The following season replay outputs were generated before the"
        )
        lines.append(
            "    league profile layer was added. Re-run run_season_replay_audit.py"
        )
        lines.append("    with --mode walk_forward for each to include profile fields.")
        lines.append("")
        for src in sorted(missing_sources):
            lines.append(f"    • {src}")
        lines.append("")

    if not present_cols or rows_with_lp == 0:
        lines.append(
            "  No league profile fields found in any evaluation CSV. "
            "Sections 20-25 are skipped."
        )
        lines.append("")
        return lines

    # Work with only rows that have LP fields
    lp_df = df[df["league_adjusted_strength"].notna()].copy()
    lp_ev = lp_df[lp_df["type_success"].notna()].copy()

    # Normalise warning flags: NaN → "" so we can test emptiness
    for _c in ("league_warning_flags",):
        if _c in lp_ev.columns:
            lp_ev[_c] = lp_ev[_c].fillna("").astype(str).str.strip()
    lp_ev["_has_warning"] = lp_ev["league_warning_flags"].str.len() > 0

    overall_lp_hits = int(lp_ev["type_success"].sum())
    overall_lp_n    = len(lp_ev)
    overall_lp_rate = overall_lp_hits / overall_lp_n if overall_lp_n else float("nan")

    lines += [
        f"  Evaluatable rows with LP fields : {overall_lp_n:,}",
        f"  Overall type-success (LP subset): {overall_lp_rate:.1%}  ({overall_lp_hits}/{overall_lp_n})",
        f"  (compare overall baseline       : {_rate(ev['type_success']):.1%}  {int(ev['type_success'].sum())}/{len(ev)})",
        "",
    ]

    # ── 20. Success by league_adjusted_strength ──────────────────────────────
    lines += _section("20. Success by League-Adjusted Strength  [diagnostic only]")
    lines.append(f"  {'Strength':<18} {'n':>5} {'hits':>5} {'rate':>7}  vs baseline")
    lines.append(_divider(52))
    baseline = overall_lp_rate
    for tier in ["HIGH", "MEDIUM", "LOW", "SUPPRESSED"]:
        grp = lp_ev[lp_ev["league_adjusted_strength"] == tier]
        hits, n = _hits_n(grp["type_success"])
        if n == 0:
            continue
        rate = hits / n
        delta = rate - baseline
        delta_s = f"  {'+' if delta >= 0 else ''}{delta:+.1%}"
        w = _warn(n, 20)
        lines.append(f"  {tier:<18} {n:>5} {hits:>5} {rate:>7.1%}{delta_s}{w}")
        agg_rows.append({"dim": "lp_strength", "key": tier, "n": n, "hits": hits, "rate": rate})
    lines.append("")

    # old recommendation_strength for comparison
    if "recommendation_strength" in lp_ev.columns:
        lines.append("  --- comparison: old recommendation_strength (same LP rows) ---")
        for tier in ["STRONG", "MODERATE", "LOW"]:
            grp = lp_ev[lp_ev["recommendation_strength"] == tier]
            hits, n = _hits_n(grp["type_success"])
            if n == 0:
                continue
            rate = hits / n
            delta = rate - baseline
            delta_s = f"  {'+' if delta >= 0 else ''}{delta:+.1%}"
            lines.append(f"  (old) {tier:<14} {n:>5} {hits:>5} {rate:>7.1%}{delta_s}")
    lines.append("")

    # ── 21. Success by league_profile ────────────────────────────────────────
    lines += _section("21. Success by League Profile  [diagnostic only]")
    lines.append(f"  {'Profile':<32} {'n':>5} {'hits':>5} {'rate':>7}  vs baseline")
    lines.append(_divider(60))
    prof_rows: list[tuple] = []
    for prof, grp in lp_ev.groupby("league_profile"):
        hits, n = _hits_n(grp["type_success"])
        if n == 0:
            continue
        rate = hits / n
        prof_rows.append((prof, n, hits, rate))
    prof_rows.sort(key=lambda x: -x[3])
    for prof, n, hits, rate in prof_rows:
        delta = rate - baseline
        delta_s = f"  {'+' if delta >= 0 else ''}{delta:+.1%}"
        w = _warn(n, 20)
        lines.append(f"  {prof:<32} {n:>5} {hits:>5} {rate:>7.1%}{delta_s}{w}")
        agg_rows.append({"dim": "lp_profile", "key": prof, "n": n, "hits": hits, "rate": rate})
    lines.append("")

    # ── 22. Success by warning flags (warned vs clean) ───────────────────────
    lines += _section("22. Success by Warning Flags  [diagnostic only]")
    lines.append(f"  {'Group':<20} {'n':>5} {'hits':>5} {'rate':>7}  vs baseline")
    lines.append(_divider(48))
    for label, mask in [("No warning (clean)", ~lp_ev["_has_warning"]),
                        ("Has warning flag",    lp_ev["_has_warning"])]:
        grp = lp_ev[mask]
        hits, n = _hits_n(grp["type_success"])
        if n == 0:
            continue
        rate = hits / n
        delta = rate - baseline
        delta_s = f"  {'+' if delta >= 0 else ''}{delta:+.1%}"
        lines.append(f"  {label:<20} {n:>5} {hits:>5} {rate:>7.1%}{delta_s}")
        agg_rows.append({"dim": "lp_warning", "key": label, "n": n, "hits": hits, "rate": rate})
    lines.append("")

    # Warning breakdown by message
    lines.append("  --- breakdown by specific warning ---")
    lines.append(f"  {'Warning (truncated)':<60} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(78))
    for flag_val, grp in lp_ev[lp_ev["_has_warning"]].groupby("league_warning_flags"):
        hits, n = _hits_n(grp["type_success"])
        if n < 5:
            continue
        rate = hits / n
        short = str(flag_val)[:58]
        lines.append(f"  {short:<60} {n:>5} {hits:>5} {rate:>7.1%}")
    lines.append("")

    # ── 23. Preferred subtype match vs no-match ───────────────────────────────
    lines += _section("23. Success — Subtype in League Preferred List  [diagnostic only]")
    lines.append(f"  {'Group':<26} {'n':>5} {'hits':>5} {'rate':>7}  vs baseline")
    lines.append(_divider(54))

    def _in_list(row: pd.Series, list_col: str) -> bool:
        lst_raw = str(row.get(list_col, "") or "")
        if not lst_raw.strip():
            return False
        lst = {s.strip().upper() for s in lst_raw.split(",")}
        sub = str(row.get("recommended_market_subtype", "") or "").upper()
        return sub in lst

    if "league_preferred_subtype" in lp_ev.columns:
        pref_mask = lp_ev.apply(lambda r: _in_list(r, "league_preferred_subtype"), axis=1)
        for label, mask in [("Subtype IS preferred",  pref_mask),
                             ("Subtype NOT preferred", ~pref_mask)]:
            grp = lp_ev[mask]
            hits, n = _hits_n(grp["type_success"])
            if n == 0:
                continue
            rate = hits / n
            delta = rate - baseline
            delta_s = f"  {'+' if delta >= 0 else ''}{delta:+.1%}"
            w = _warn(n, 20)
            lines.append(f"  {label:<26} {n:>5} {hits:>5} {rate:>7.1%}{delta_s}{w}")
            agg_rows.append({"dim": "lp_preferred_match", "key": label, "n": n, "hits": hits, "rate": rate})
    lines.append("")

    # ── 24. Suppressed subtype match vs no-match ─────────────────────────────
    lines += _section("24. Success — Subtype in League Suppressed List  [diagnostic only]")
    lines.append(f"  {'Group':<26} {'n':>5} {'hits':>5} {'rate':>7}  vs baseline")
    lines.append(_divider(54))

    if "league_suppressed_subtype" in lp_ev.columns:
        supp_mask = lp_ev.apply(lambda r: _in_list(r, "league_suppressed_subtype"), axis=1)
        for label, mask in [("Subtype IS suppressed",  supp_mask),
                             ("Subtype NOT suppressed", ~supp_mask)]:
            grp = lp_ev[mask]
            hits, n = _hits_n(grp["type_success"])
            if n == 0:
                continue
            rate = hits / n
            delta = rate - baseline
            delta_s = f"  {'+' if delta >= 0 else ''}{delta:+.1%}"
            w = _warn(n, 20)
            lines.append(f"  {label:<26} {n:>5} {hits:>5} {rate:>7.1%}{delta_s}{w}")
            agg_rows.append({"dim": "lp_suppressed_match", "key": label, "n": n, "hits": hits, "rate": rate})
    lines.append("")

    # ── 25. A-Tier / B-Tier / C-Tier / No-Go buckets ─────────────────────────
    lines += _section("25. Diagnostic Quality Buckets  [A-Tier / B-Tier / C-Tier / No-Go]")
    lines += [
        "  > Bucket definitions (diagnostic only — no betting claims):",
        "  >",
        "  > **A-Tier**: league_adjusted_strength=HIGH + no warning flags",
        "  >             + subtype in {UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2}",
        "  >             + chaos_bucket in {low (<4), medium (4-6)}",
        "  >",
        "  > **No-Go** : league_adjusted_strength=SUPPRESSED",
        "  >             OR has warning flag",
        "  >             OR subtype in {BOTH_OVER25_BTTS, BTTS}",
        "  >             OR subtype=OVER_25 in non-goal-friendly leagues",
        "  >             (goal-friendly: Eredivisie, 2. Bundesliga)",
        "  >",
        "  > **B-Tier**: not A, not No-Go + strength in {HIGH, MEDIUM} + no warning",
        "  > **C-Tier**: everything else (LOW strength or warned but not fully No-Go)",
        "",
    ]

    # Build masks
    sub_col   = "recommended_market_subtype"
    chaos_col = "chaos_bucket"

    lp_ev["_sub_upper"] = lp_ev[sub_col].astype(str).str.upper()
    has_chaos = chaos_col in lp_ev.columns

    mask_a = (
        (lp_ev["league_adjusted_strength"] == "HIGH")
        & (~lp_ev["_has_warning"])
        & (lp_ev["_sub_upper"].isin(_A_TIER_SUBTYPES))
    )
    if has_chaos:
        mask_a = mask_a & lp_ev[chaos_col].isin(_CHAOS_SAFE)

    # No-Go
    mask_btts_etc = (
        lp_ev["_sub_upper"].isin({"BOTH_OVER25_BTTS", "BTTS"})
        | (
            (lp_ev["_sub_upper"] == "OVER_25")
            & (~lp_ev["league"].isin(_GOAL_FRIENDLY_LEAGUES))
        )
    )
    mask_nogo = (
        (lp_ev["league_adjusted_strength"] == "SUPPRESSED")
        | lp_ev["_has_warning"]
        | mask_btts_etc
    )

    mask_b = (~mask_a) & (~mask_nogo) & (lp_ev["league_adjusted_strength"].isin(["HIGH", "MEDIUM"]))
    mask_c = (~mask_a) & (~mask_nogo) & (~mask_b)

    lines.append(f"  {'Bucket':<12} {'n':>5} {'hits':>5} {'rate':>7}  vs LP-baseline")
    lines.append(_divider(50))
    bucket_results: list[tuple] = []
    for label, mask in [("A-Tier", mask_a), ("B-Tier", mask_b),
                         ("C-Tier", mask_c), ("No-Go",  mask_nogo)]:
        grp = lp_ev[mask]
        hits, n = _hits_n(grp["type_success"])
        if n == 0:
            lines.append(f"  {label:<12} {0:>5} {0:>5}     n/a")
            continue
        rate = hits / n
        delta = rate - baseline
        delta_s = f"  {'+' if delta >= 0 else ''}{delta:+.1%}"
        w = _warn(n, 20)
        lines.append(f"  {label:<12} {n:>5} {hits:>5} {rate:>7.1%}{delta_s}{w}")
        bucket_results.append((label, n, hits, rate, delta))
        agg_rows.append({"dim": "lp_bucket", "key": label, "n": n, "hits": hits, "rate": rate})
    lines.append("")

    # A-Tier breakdown by league
    lines.append("  --- A-Tier breakdown by league ---")
    lines.append(f"  {'League':<22} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(40))
    if "league" in lp_ev.columns:
        for league, grp in lp_ev[mask_a].groupby("league"):
            hits, n = _hits_n(grp["type_success"])
            if n == 0: continue
            rate = hits / n
            w = _warn(n, 10)
            lines.append(f"  {league:<22} {n:>5} {hits:>5} {rate:>7.1%}{w}")
    lines.append("")

    # A-Tier breakdown by subtype
    lines.append("  --- A-Tier breakdown by subtype ---")
    lines.append(f"  {'Subtype':<26} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(44))
    for subtype, grp in lp_ev[mask_a].groupby(sub_col):
        hits, n = _hits_n(grp["type_success"])
        if n == 0: continue
        rate = hits / n
        w = _warn(n, 10)
        lines.append(f"  {subtype:<26} {n:>5} {hits:>5} {rate:>7.1%}{w}")
    lines.append("")

    # No-Go breakdown by reason
    lines.append("  --- No-Go: reason distribution ---")
    lines.append(f"  {'Reason':<30} {'n':>5}")
    lines.append(_divider(38))
    reasons = {
        "SUPPRESSED strength":      (lp_ev["league_adjusted_strength"] == "SUPPRESSED").sum(),
        "Has warning flag":          lp_ev["_has_warning"].sum(),
        "BTTS/BOTH_OVER25_BTTS":    lp_ev["_sub_upper"].isin({"BOTH_OVER25_BTTS","BTTS"}).sum(),
        "OVER_25 non-goal-friendly": ((lp_ev["_sub_upper"]=="OVER_25") & (~lp_ev["league"].isin(_GOAL_FRIENDLY_LEAGUES))).sum(),
    }
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"  {reason:<30} {int(count):>5}")
    lines.append(
        "  (Note: a single row may satisfy multiple No-Go criteria)"
    )
    lines.append("")

    # ── Summary narrative ────────────────────────────────────────────────────
    lines += _section("26. League Profile Diagnostic Summary")

    # Is league_adjusted_strength a better discriminator than old strength?
    lp_high_rate  = _rate(lp_ev[lp_ev["league_adjusted_strength"]=="HIGH"]["type_success"])
    lp_supp_rate  = _rate(lp_ev[lp_ev["league_adjusted_strength"]=="SUPPRESSED"]["type_success"])
    old_strong_rate = _rate(lp_ev[lp_ev["recommendation_strength"]=="STRONG"]["type_success"]) \
        if "recommendation_strength" in lp_ev.columns else float("nan")
    old_low_rate = _rate(lp_ev[lp_ev["recommendation_strength"]=="LOW"]["type_success"]) \
        if "recommendation_strength" in lp_ev.columns else float("nan")

    spread_new = (lp_high_rate - lp_supp_rate) if not (math.isnan(lp_high_rate) or math.isnan(lp_supp_rate)) else float("nan")
    spread_old = (old_strong_rate - old_low_rate) if not (math.isnan(old_strong_rate) or math.isnan(old_low_rate)) else float("nan")

    def _yn(val: bool) -> str:
        return "✅ YES" if val else "❌ NO"

    # Determine A-Tier, No-Go rates
    a_rate  = next((r for l, n, h, r, d in bucket_results if l == "A-Tier"),  float("nan"))
    ng_rate = next((r for l, n, h, r, d in bucket_results if l == "No-Go"),   float("nan"))

    if not math.isnan(spread_new) and not math.isnan(spread_old):
        better_discriminator_answer = _yn(spread_new > spread_old)
    elif not math.isnan(spread_new):
        better_discriminator_answer = f"✅ NEW spread={spread_new:+.1%} (old strength not comparable — insufficient tier distribution in LP rows)"
    else:
        better_discriminator_answer = "⚠ Cannot determine (insufficient data)"
    better_discriminator = False  # only used for _yn fallback; actual answer set above
    a_better_baseline    = (not math.isnan(a_rate)  and a_rate  > overall_lp_rate)
    nogo_worse_baseline  = (not math.isnan(ng_rate) and ng_rate < overall_lp_rate)

    # Best profile
    best_prof = prof_rows[0][0] if prof_rows else "—"
    best_rate = prof_rows[0][3] if prof_rows else float("nan")
    worst_prof = prof_rows[-1][0] if prof_rows else "—"
    worst_rate = prof_rows[-1][3] if prof_rows else float("nan")

    lines += [
        f"  Q1. Does league_adjusted_strength separate better than old strength?",
        f"      New spread (HIGH-SUPPRESSED): {spread_new:+.1%}" if not math.isnan(spread_new) else "      New spread: n/a",
        f"      Old spread (STRONG-LOW)     : {spread_old:+.1%}" if not math.isnan(spread_old) else "      Old spread: n/a",
        f"      Answer: {better_discriminator_answer}",
        "",
        f"  Q2. Is A-Tier better than the LP-subset baseline ({overall_lp_rate:.1%})?",
        f"      A-Tier rate: {a_rate:.1%}" if not math.isnan(a_rate) else "      A-Tier rate: n/a",
        f"      Answer: {_yn(a_better_baseline)}",
        "",
        f"  Q3. Is No-Go worse than the LP-subset baseline ({overall_lp_rate:.1%})?",
        f"      No-Go rate: {ng_rate:.1%}" if not math.isnan(ng_rate) else "      No-Go rate: n/a",
        f"      Answer: {_yn(nogo_worse_baseline)}",
        "",
        f"  Q4. Which league profile works best?",
        f"      Best : {best_prof:<35} {best_rate:.1%}" if not math.isnan(best_rate) else "      Best : —",
        f"      Worst: {worst_prof:<35} {worst_rate:.1%}" if not math.isnan(worst_rate) else "      Worst: —",
        "",
        "  *League profile sections are diagnostic only. No betting, ROI, or staking claims.*",
        "",
    ]

    return lines


# ---------------------------------------------------------------------------
# Main analyser
# ---------------------------------------------------------------------------

def analyse(df: pd.DataFrame) -> tuple[list[str], pd.DataFrame]:
    ev      = df[df["type_success"].notna()].copy()
    sub_ev  = df[df["subtype_success"].notna()].copy()

    lines: list[str]     = []
    agg_rows: list[dict] = []

    # ── Header ──────────────────────────────────────────────────────────────
    n_leagues  = df["league"].nunique() if "league" in df.columns else "?"
    n_combos   = df.groupby(["league", "season"]).ngroups if all(c in df.columns for c in ["league","season"]) else "?"
    n_total    = len(df)
    n_eval     = len(ev)
    overall    = _rate(ev["type_success"])

    league_list = sorted(df["league"].dropna().unique()) if "league" in df.columns else []

    lines += [
        "# Walk-Forward Season Replay — Final Aggregate Analysis",
        "",
        "> **Diagnostic only. No betting rules. No ROI claims.**  ",
        "> Mode: **TRUE walk-forward ML** (LogisticRegression retrained per cutoff)",
        "",
        "## Dataset Overview",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Leagues | {n_leagues} |",
        f"| Leagues covered | {', '.join(league_list)} |",
        f"| Season-league combos | {n_combos} |",
        f"| Total predicted matches | {n_total:,} |",
        f"| Evaluatable (type_success known) | {n_eval:,} |",
        f"| Overall type success rate | **{overall:.1%}** |",
        "",
    ]

    # ── 1. Runs inventory ───────────────────────────────────────────────────
    lines += _section("1. Runs Inventory")
    lines.append(f"  {'League':<22} {'Season':<8} {'rows':>5} {'ev':>5} {'rate':>7}")
    lines.append(_divider(55))
    for (league, season), grp in df.groupby(["league", "season"]):
        g = grp[grp["type_success"].notna()]
        hits, n = _hits_n(g["type_success"])
        lines.append(f"  {league:<22} {str(season):<8} {len(grp):>5} {n:>5} {hits/n:>7.1%}" if n else
                     f"  {league:<22} {str(season):<8} {len(grp):>5} {n:>5}     n/a")
    lines.append(f"\n  {'TOTAL':<30} {n_total:>5} {n_eval:>5} {overall:>7.1%}")
    lines.append("")

    # ── 2. Overall success by league ────────────────────────────────────────
    lines += _section("2. Overall Success by League")
    lines.append(f"  {'League':<22} {'seasons':>7} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(50))
    league_summary: list[tuple] = []
    for league, grp in ev.groupby("league"):
        seasons = grp["season"].nunique()
        hits, n = _hits_n(grp["type_success"])
        rate = hits / n if n else float("nan")
        league_summary.append((league, seasons, n, hits, rate))
        agg_rows.append({"dim": "league", "key": league, "seasons": seasons, "n": n,
                         "hits": hits, "rate": rate})
    league_summary.sort(key=lambda x: -x[4])
    for lg, seas, n, hits, rate in league_summary:
        lines.append(f"  {lg:<22} {seas:>7} {n:>5} {hits:>5} {rate:>7.1%}")
    lines.append("")

    # ── 3. Overall success by season ────────────────────────────────────────
    lines += _section("3. Overall Success by Season")
    lines.append(f"  {'League + Season':<32} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(52))
    for (league, season), grp in ev.groupby(["league", "season"]):
        hits, n = _hits_n(grp["type_success"])
        lines.append(f"  {str(league)+' '+str(season):<32} {n:>5} {hits:>5} {hits/n:>7.1%}" if n else
                     f"  {str(league)+' '+str(season):<32} {n:>5} {0:>5}     n/a")
    lines.append("")

    # ── 4. Success by market type (all leagues) ─────────────────────────────
    lines += _section("4. Success by Recommended Market Type — All Leagues")
    lines += _type_table(ev, ["recommended_market_type"], "type_success", lw=22, sort_col="rate")

    # ── 5. Success by subtype (all leagues) ─────────────────────────────────
    lines += _section("5. Success by Recommended Market Subtype — All Leagues")
    lines.append(f"  {'Subtype':<26} {'n':>5} {'hits':>5} {'rate':>7}  {'Parent':<18}")
    lines.append(_divider(72))
    subtype_agg: list[dict] = []
    for subtype, sg in sub_ev.groupby("recommended_market_subtype"):
        n = len(sg); hits = int(sg["subtype_success"].sum())
        rate = hits / n if n else float("nan")
        parent = sg["recommended_market_type"].mode().iloc[0] if n > 0 else "?"
        subtype_agg.append({"subtype": subtype, "n": n, "hits": hits, "rate": rate, "parent": parent})
        agg_rows.append({"dim": "subtype", "key": subtype, "n": n, "hits": hits,
                         "rate": rate, "parent_type": parent})
    subtype_agg.sort(key=lambda x: -(x["rate"] if not math.isnan(x["rate"]) else 0))
    for r in subtype_agg:
        w = _warn(r["n"])
        rate_s = f"{r['rate']:>7.1%}" if not math.isnan(r["rate"]) else "    n/a"
        lines.append(f"  {r['subtype']:<26} {r['n']:>5} {r['hits']:>5} {rate_s}  {r['parent']:<18}{w}")
    lines.append("")

    # ── 6. League × market type ─────────────────────────────────────────────
    lines += _section("6. Success by League × Market Type")
    lines.append(f"  {'League + Type':<38} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(60))
    lg_type_rows: list[tuple] = []
    for (league, mtype), grp in ev.groupby(["league", "recommended_market_type"]):
        hits, n = _hits_n(grp["type_success"])
        if n == 0: continue
        lg_type_rows.append((league, mtype, n, hits, hits/n))
    # Sort by league order, then by rate descending within each league
    def _lg_key(r):
        lg_idx = LEAGUE_ORDER.index(r[0]) if r[0] in LEAGUE_ORDER else 99
        return (lg_idx, -r[4])
    lg_type_rows.sort(key=_lg_key)
    prev_lg = None
    for league, mtype, n, hits, rate in lg_type_rows:
        if league != prev_lg:
            lines.append("")
            prev_lg = league
        w = _warn(n)
        lines.append(f"  {str(league)+' | '+mtype:<38} {n:>5} {hits:>5} {rate:>7.1%}{w}")
    lines.append("")

    # ── 7. League × subtype ─────────────────────────────────────────────────
    lines += _section("7. Success by League × Market Subtype")
    lines.append(f"  {'League + Subtype':<42} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(64))
    lg_sub_rows: list[tuple] = []
    for (league, subtype), sg in sub_ev.groupby(["league", "recommended_market_subtype"]):
        n = len(sg); hits = int(sg["subtype_success"].sum())
        if n == 0: continue
        rate = hits / n
        lg_sub_rows.append((league, subtype, n, hits, rate))
    lg_sub_rows.sort(key=lambda r: (LEAGUE_ORDER.index(r[0]) if r[0] in LEAGUE_ORDER else 99, -r[4]))
    prev_lg = None
    for league, subtype, n, hits, rate in lg_sub_rows:
        if league != prev_lg:
            lines.append("")
            prev_lg = league
        w = _warn(n)
        lines.append(f"  {str(league)+' | '+subtype:<42} {n:>5} {hits:>5} {rate:>7.1%}{w}")
    lines.append("")

    # ── 8. Control bucket ───────────────────────────────────────────────────
    lines += _section("8. Success by Control Bucket")
    lines.append(f"  {'Bucket':<22} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(44))
    bucket_order = ["very_low (<3)", "low (3-5)", "medium (5-7)", "high (7-10)"]
    for bucket in bucket_order:
        grp = ev[ev.get("ctrl_bucket", pd.Series(dtype=str)) == bucket] if "ctrl_bucket" in ev.columns else pd.DataFrame()
        if "ctrl_bucket" in ev.columns:
            grp = ev[ev["ctrl_bucket"] == bucket]
        if len(grp) == 0: continue
        hits, n = _hits_n(grp["type_success"])
        lines.append(_row_line(bucket, n, hits, lw=22))
    lines.append("")

    # ── 9. Chaos bucket ─────────────────────────────────────────────────────
    lines += _section("9. Success by Chaos Bucket")
    lines.append(f"  {'Bucket':<22} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(44))
    chaos_order = ["low (<4)", "medium (4-6)", "high (6-10)"]
    for bucket in chaos_order:
        if "chaos_bucket" not in ev.columns: break
        grp = ev[ev["chaos_bucket"] == bucket]
        if len(grp) == 0: continue
        hits, n = _hits_n(grp["type_success"])
        lines.append(_row_line(bucket, n, hits, lw=22))
    lines.append("")

    # ── 10. Favorite side ───────────────────────────────────────────────────
    lines += _section("10. Success by Favorite Side")
    lines += _type_table(
        ev[ev["fav_side"].notna()] if "fav_side" in ev.columns else ev,
        ["fav_side"], "type_success", lw=24, sort_col="rate"
    )

    # ── 11. Confidence ──────────────────────────────────────────────────────
    lines += _section("11. Success by Confidence Level")
    lines.append(f"  {'Confidence':<18} {'n':>5} {'hits':>5} {'rate':>7}")
    lines.append(_divider(40))
    for conf in ["HIGH", "MEDIUM", "LOW", "NO-CONFIDENCE"]:
        if "confidence" not in ev.columns: break
        grp = ev[ev["confidence"] == conf]
        if len(grp) == 0: continue
        hits, n = _hits_n(grp["type_success"])
        lines.append(_row_line(conf, n, hits, lw=18))
    lines.append("")

    # ── 12. Recommendation strength ─────────────────────────────────────────
    lines += _section("12. Success by Recommendation Strength")
    lines += _type_table(
        ev[ev["recommendation_strength"].notna()] if "recommendation_strength" in ev.columns else ev,
        ["recommendation_strength"], "type_success", lw=22, sort_col="rate"
    )

    # ── 13. Top 30 misses ───────────────────────────────────────────────────
    lines += _section("13. Top 30 Misses  (type_success = False, sorted by goals desc)")
    misses = df[df["type_success"] == 0].copy()
    if "actual_total_goals" in misses.columns:
        misses = misses.sort_values("actual_total_goals", ascending=False).head(30)
    else:
        misses = misses.head(30)
    lines.append(f"  {'Match':<32} {'League':<14} {'Type':<16} {'Subtype':<22} {'Res':<4} {'G':>3}")
    lines.append("  " + "-" * 98)
    for _, row in misses.iterrows():
        game   = f"{row.get('home_team','?')} v {row.get('away_team','?')}"[:30]
        league = str(row.get("league","?"))[:13]
        mtype  = str(row.get("recommended_market_type","?"))
        stype  = str(row.get("recommended_market_subtype","?"))
        result = str(row.get("actual_result","?"))
        goals  = row.get("actual_total_goals", float("nan"))
        gstr   = f"{goals:.0f}" if isinstance(goals, float) and not math.isnan(goals) else "?"
        lines.append(f"  {game:<32} {league:<14} {mtype:<16} {stype:<22} {result:<4} {gstr:>3}")
    lines.append("")

    # ── 14. Top 30 hits ─────────────────────────────────────────────────────
    lines += _section("14. Top 30 Clean Hits  (type_success = True, sorted by goals desc)")
    hits_df = df[df["type_success"] == 1].copy()
    if "actual_total_goals" in hits_df.columns:
        hits_df = hits_df.sort_values("actual_total_goals", ascending=False).head(30)
    else:
        hits_df = hits_df.head(30)
    lines.append(f"  {'Match':<32} {'League':<14} {'Type':<16} {'Subtype':<22} {'Res':<4} {'G':>3}")
    lines.append("  " + "-" * 98)
    for _, row in hits_df.iterrows():
        game   = f"{row.get('home_team','?')} v {row.get('away_team','?')}"[:30]
        league = str(row.get("league","?"))[:13]
        mtype  = str(row.get("recommended_market_type","?"))
        stype  = str(row.get("recommended_market_subtype","?"))
        result = str(row.get("actual_result","?"))
        goals  = row.get("actual_total_goals", float("nan"))
        gstr   = f"{goals:.0f}" if isinstance(goals, float) and not math.isnan(goals) else "?"
        lines.append(f"  {game:<32} {league:<14} {mtype:<16} {stype:<22} {result:<4} {gstr:>3}")
    lines.append("")

    # ── 15. Stability assessment n>=50 ──────────────────────────────────────
    lines += _section("15. Pattern Stability Assessment (n ≥ 50)")

    stable, unstable, bad = [], [], []
    for r in subtype_agg:
        if r["n"] < 50 or math.isnan(r["rate"]): continue
        if r["rate"] >= 0.70:   stable.append(r)
        elif r["rate"] < 0.55:  bad.append(r)
        else:                   unstable.append(r)

    lines += ["### ✅ Stable Patterns  (n≥50, rate≥70%)", ""]
    if stable:
        for r in sorted(stable, key=lambda x: -x["rate"]):
            lines.append(f"  {r['subtype']:<28} {r['rate']:.1%}  ({r['hits']}/{r['n']})  [{r['parent']}]")
    else:
        lines.append("  — none —")
    lines.append("")

    lines += ["### ⚠ Unstable / Marginal Patterns  (n≥50, 55%≤rate<70%)", ""]
    if unstable:
        for r in sorted(unstable, key=lambda x: -x["rate"]):
            lines.append(f"  {r['subtype']:<28} {r['rate']:.1%}  ({r['hits']}/{r['n']})  [{r['parent']}]")
    else:
        lines.append("  — none —")
    lines.append("")

    lines += ["### ❌ Weak / Bad Patterns  (n≥50, rate<55%)", ""]
    if bad:
        for r in sorted(bad, key=lambda x: x["rate"]):
            lines.append(f"  {r['subtype']:<28} {r['rate']:.1%}  ({r['hits']}/{r['n']})  [{r['parent']}]")
    else:
        lines.append("  — none —")
    lines.append("")

    # ── 16. Special cross-league probes ─────────────────────────────────────
    lines += _section("16. Cross-League Probe Table")
    lines.append(
        "  Answers specific diagnostic questions using subtype_success or type_success."
    )
    lines.append("")

    def _probe(label: str, mask: pd.Series, use_col: str = "subtype_success") -> str:
        grp = df[mask & df[use_col].notna()]
        n = len(grp)
        if n == 0:
            return f"  {label:<56}  n/a      (n=0)"
        hits = int(grp[use_col].sum())
        rate = hits / n
        w = "  ⚠ n<50" if n < 50 else ""
        return f"  {label:<56}  {rate:.1%}  ({hits}/{n}){w}"

    def _mask(league=None, subtype=None, mtype=None) -> pd.Series:
        m = pd.Series([True] * len(df), index=df.index)
        if league  is not None: m &= df["league"] == league
        if subtype is not None: m &= df["recommended_market_subtype"] == subtype
        if mtype   is not None: m &= df["recommended_market_type"] == mtype
        return m

    probes = [
        # DOUBLE_CHANCE cross-league
        ("DOUBLE_CHANCE_1X — Premier League",  _probe("DOUBLE_CHANCE_1X (Premier League)",  _mask("Premier League","DOUBLE_CHANCE_1X"))),
        ("DOUBLE_CHANCE_1X — La Liga",         _probe("DOUBLE_CHANCE_1X (La Liga)",         _mask("La Liga",        "DOUBLE_CHANCE_1X"))),
        ("DOUBLE_CHANCE_1X — Serie A",         _probe("DOUBLE_CHANCE_1X (Serie A)",         _mask("Serie A",        "DOUBLE_CHANCE_1X"))),
        ("DOUBLE_CHANCE_1X — Ligue 1",         _probe("DOUBLE_CHANCE_1X (Ligue 1)",         _mask("Ligue 1",        "DOUBLE_CHANCE_1X"))),
        ("DOUBLE_CHANCE_1X — Eredivisie",      _probe("DOUBLE_CHANCE_1X (Eredivisie)",      _mask("Eredivisie",     "DOUBLE_CHANCE_1X"))),
        ("DOUBLE_CHANCE_1X — 2. Bundesliga",   _probe("DOUBLE_CHANCE_1X (2. Bundesliga)",   _mask("2. Bundesliga",  "DOUBLE_CHANCE_1X"))),
        ("DOUBLE_CHANCE_X2 — Premier League",  _probe("DOUBLE_CHANCE_X2 (Premier League)",  _mask("Premier League","DOUBLE_CHANCE_X2"))),
        ("DOUBLE_CHANCE_X2 — La Liga",         _probe("DOUBLE_CHANCE_X2 (La Liga)",         _mask("La Liga",        "DOUBLE_CHANCE_X2"))),
        ("DOUBLE_CHANCE_X2 — Serie A",         _probe("DOUBLE_CHANCE_X2 (Serie A)",         _mask("Serie A",        "DOUBLE_CHANCE_X2"))),
        ("DOUBLE_CHANCE_X2 — Ligue 1",         _probe("DOUBLE_CHANCE_X2 (Ligue 1)",         _mask("Ligue 1",        "DOUBLE_CHANCE_X2"))),
        ("DOUBLE_CHANCE_X2 — Eredivisie",      _probe("DOUBLE_CHANCE_X2 (Eredivisie)",      _mask("Eredivisie",     "DOUBLE_CHANCE_X2"))),
        ("DOUBLE_CHANCE_X2 — 2. Bundesliga",   _probe("DOUBLE_CHANCE_X2 (2. Bundesliga)",   _mask("2. Bundesliga",  "DOUBLE_CHANCE_X2"))),
        # AVOID
        ("AVOID — Premier League",             _probe("AVOID (Premier League)",             _mask("Premier League",mtype="AVOID"), "type_success")),
        ("AVOID — La Liga",                    _probe("AVOID (La Liga)",                    _mask("La Liga",        mtype="AVOID"), "type_success")),
        ("AVOID — Serie A",                    _probe("AVOID (Serie A)",                    _mask("Serie A",        mtype="AVOID"), "type_success")),
        ("AVOID — Ligue 1",                    _probe("AVOID (Ligue 1)",                    _mask("Ligue 1",        mtype="AVOID"), "type_success")),
        ("AVOID — Eredivisie",                 _probe("AVOID (Eredivisie)",                 _mask("Eredivisie",     mtype="AVOID"), "type_success")),
        ("AVOID — 2. Bundesliga",              _probe("AVOID (2. Bundesliga)",              _mask("2. Bundesliga",  mtype="AVOID"), "type_success")),
        # UNDER_35
        ("UNDER_35 — Premier League",          _probe("UNDER_35 (Premier League)",          _mask("Premier League","UNDER_35"))),
        ("UNDER_35 — La Liga",                 _probe("UNDER_35 (La Liga)",                 _mask("La Liga",        "UNDER_35"))),
        ("UNDER_35 — Serie A",                 _probe("UNDER_35 (Serie A)",                 _mask("Serie A",        "UNDER_35"))),
        ("UNDER_35 — Ligue 1",                 _probe("UNDER_35 (Ligue 1)",                 _mask("Ligue 1",        "UNDER_35"))),
        ("UNDER_35 — Eredivisie",              _probe("UNDER_35 (Eredivisie)",              _mask("Eredivisie",     "UNDER_35"))),
        ("UNDER_35 — 2. Bundesliga",           _probe("UNDER_35 (2. Bundesliga)",           _mask("2. Bundesliga",  "UNDER_35"))),
        # BTTS / BOTH_OVER25_BTTS
        ("BTTS (subtype) — all leagues",       _probe("BTTS subtype — ALL",                 pd.Series([True]*len(df), index=df.index) & (df["recommended_market_subtype"]=="BTTS"))),
        ("BTTS — Eredivisie",                  _probe("BTTS subtype (Eredivisie)",          _mask("Eredivisie","BTTS"))),
        ("BTTS — 2. Bundesliga",               _probe("BTTS subtype (2. Bundesliga)",       _mask("2. Bundesliga","BTTS"))),
        ("BTTS — La Liga",                     _probe("BTTS subtype (La Liga)",             _mask("La Liga","BTTS"))),
        ("BOTH_OVER25_BTTS — all leagues",     _probe("BOTH_OVER25_BTTS — ALL",            pd.Series([True]*len(df), index=df.index) & (df["recommended_market_subtype"]=="BOTH_OVER25_BTTS"))),
        ("BOTH_OVER25_BTTS — Eredivisie",      _probe("BOTH_OVER25_BTTS (Eredivisie)",     _mask("Eredivisie","BOTH_OVER25_BTTS"))),
        ("BOTH_OVER25_BTTS — 2. Bundesliga",   _probe("BOTH_OVER25_BTTS (2. Bundesliga)",  _mask("2. Bundesliga","BOTH_OVER25_BTTS"))),
        # OVER_25
        ("OVER_25 — all leagues",              _probe("OVER_25 — ALL",                     pd.Series([True]*len(df), index=df.index) & (df["recommended_market_subtype"]=="OVER_25"))),
        ("OVER_25 — Eredivisie",               _probe("OVER_25 (Eredivisie)",              _mask("Eredivisie","OVER_25"))),
        ("OVER_25 — 2. Bundesliga",            _probe("OVER_25 (2. Bundesliga)",           _mask("2. Bundesliga","OVER_25"))),
        ("OVER_25 — La Liga",                  _probe("OVER_25 (La Liga)",                 _mask("La Liga","OVER_25"))),
        ("OVER_25 — Premier League",           _probe("OVER_25 (Premier League)",          _mask("Premier League","OVER_25"))),
        # BTTS_OVER type by league
        ("BTTS_OVER type — Eredivisie",        _probe("BTTS_OVER type (Eredivisie)",       _mask("Eredivisie",mtype="BTTS_OVER"), "type_success")),
        ("BTTS_OVER type — 2. Bundesliga",     _probe("BTTS_OVER type (2. Bundesliga)",    _mask("2. Bundesliga",mtype="BTTS_OVER"), "type_success")),
        ("BTTS_OVER type — La Liga",           _probe("BTTS_OVER type (La Liga)",          _mask("La Liga",mtype="BTTS_OVER"), "type_success")),
        ("BTTS_OVER type — Premier League",    _probe("BTTS_OVER type (Premier League)",   _mask("Premier League",mtype="BTTS_OVER"), "type_success")),
        ("BTTS_OVER type — Serie A",           _probe("BTTS_OVER type (Serie A)",          _mask("Serie A",mtype="BTTS_OVER"), "type_success")),
        ("BTTS_OVER type — Ligue 1",           _probe("BTTS_OVER type (Ligue 1)",          _mask("Ligue 1",mtype="BTTS_OVER"), "type_success")),
        # DIRECTION
        ("DIRECTION_HOME — all leagues",       _probe("DIRECTION_HOME — ALL",              pd.Series([True]*len(df), index=df.index) & (df["recommended_market_subtype"]=="DIRECTION_HOME"))),
    ]

    lines.append(f"  {'Pattern':<58}  {'rate':>6}  (hits/n)")
    lines.append("  " + "-" * 82)
    for _label, result in probes:
        lines.append(result)
    lines.append("")

    # ── 17. League profiles ─────────────────────────────────────────────────
    lines += _section("17. League-Specific Profiles")

    def _lg_profile(league: str) -> list[str]:
        lg_ev  = ev[ev["league"] == league]
        lg_sub = sub_ev[sub_ev["league"] == league]
        if len(lg_ev) == 0:
            return [f"### {league}", "  No data.", ""]

        overall_hits, overall_n = _hits_n(lg_ev["type_success"])
        overall_rate = overall_hits / overall_n if overall_n else float("nan")

        out = [f"### {league}  ({overall_hits}/{overall_n} = {overall_rate:.1%} overall)", ""]
        out.append(f"  {'Type':<22} {'n':>5} {'hits':>5} {'rate':>7}")
        out.append("  " + "-" * 42)
        for mtype in TYPE_ORDER:
            grp = lg_ev[lg_ev["recommended_market_type"] == mtype]
            hits, n = _hits_n(grp["type_success"])
            if n == 0: continue
            w = _warn(n)
            out.append(f"  {mtype:<22} {n:>5} {hits:>5} {hits/n:>7.1%}{w}")
        out.append("")

        out.append(f"  {'Subtype':<26} {'n':>5} {'hits':>5} {'rate':>7}")
        out.append("  " + "-" * 46)
        sub_stats = []
        for subtype, sg in lg_sub.groupby("recommended_market_subtype"):
            n = len(sg); hits = int(sg["subtype_success"].sum())
            if n == 0: continue
            sub_stats.append((subtype, n, hits, hits/n))
        for subtype, n, hits, rate in sorted(sub_stats, key=lambda x: -x[3]):
            w = _warn(n)
            out.append(f"  {subtype:<26} {n:>5} {hits:>5} {rate:>7.1%}{w}")
        out.append("")
        return out

    for league in LEAGUE_ORDER:
        if league in df["league"].values:
            lines += _lg_profile(league)

    # ── 18. Recommendations for next layer ──────────────────────────────────
    lines += _section("18. Recommendations for Next Report-Layer Step")
    lines += [
        "Based on the aggregate evidence above (diagnostic only, no betting rules):",
        "",
        "### Signal reliability tiers",
        "",
        "| Tier | Subtypes | Action |",
        "|---|---|---|",
        "| **Tier 1 — Reliable** | UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2, AVOID | Show prominently; confirm with odds before reporting |",
        "| **Tier 2 — Conditional** | OVER_25 (Eredivisie/2.Bundesliga only), DIRECTION_HOME | Show with league filter; suppress in La Liga/Serie A |",
        "| **Tier 3 — Noisy** | BTTS, BOTH_OVER25_BTTS | Flag as high-variance; consider splitting into stronger sub-conditions |",
        "| **Tier 4 — Suppress** | BOTH_OVER25_BTTS (La Liga/Serie A) | Very low hit rate; suppress or warn |",
        "",
        "### League-specific profile recommendations",
        "",
        "| League | Profile | Key signal |",
        "|---|---|---|",
        "| Premier League | Control-heavy, low-chaos | DOUBLE_CHANCE preferred; BTTS_OVER unreliable |",
        "| La Liga | Control + UNDER | UNDER_35 dominant; DOUBLE_CHANCE_1X strong; BTTS weak |",
        "| Serie A | Control + UNDER | Similar to La Liga; monitor UNDER_35 volume |",
        "| Ligue 1 | Mixed | DOUBLE_CHANCE reliable; BTTS volatile |",
        "| Eredivisie | Goals league | BTTS_OVER type acceptable (70%+); BOTH_OVER25_BTTS still weak subtype |",
        "| 2. Bundesliga | Goals + DOUBLE_CHANCE | Profile TBD — check BTTS_OVER vs DOUBLE_CHANCE split |",
        "",
        "### Next step suggestions (diagnostic only)",
        "",
        "1. **Add UNDER_35 trigger condition to all 6 league daily reports** — highest-confidence signal.",
        "2. **Add league filter to BTTS_OVER subtype display**: show OVER_25 in Eredivisie/2.Bundesliga, suppress in La Liga/Serie A/Premier League.",
        "3. **Split BOTH_OVER25_BTTS** into separate OVER_25 + BTTS conditions; the combined AND requirement is systematically too strict.",
        "4. **Add n-warning badge** to subtypes with n<50 in the season replay summary.",
        "5. **Run 3 more seasons per league** to stabilise subtype rates (current n<50 for many league-subtype pairs).",
        "",
    ]

    # ── 19-25. League-Aware Profile sections ────────────────────────────────
    lines += _build_lp_sections(df, ev, agg_rows)

    # ── Footer ──────────────────────────────────────────────────────────────
    lines += [
        "---",
        "*Aggregate diagnostic report. No betting, staking, or ROI claims.*",
        "*All results are from TRUE walk-forward ML (LogisticRegression retrained per cutoff).*",
    ]

    agg_df = pd.DataFrame(agg_rows)
    return lines, agg_df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  Walk-Forward Aggregate Analyser")
    print("=" * 60)
    print("\nLoading evaluation CSVs…")
    df = load_all()

    print("\nRunning analysis…")
    lines, agg_df = analyse(df)

    md_path  = OUT_DIR / "walk_forward_aggregate_summary.md"
    csv_path = OUT_DIR / "walk_forward_aggregate_summary.csv"

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    agg_df.to_csv(csv_path, index=False)

    print(f"\n  OK {md_path.name}  ({md_path.stat().st_size // 1024} KB)")
    print(f"  OK {csv_path.name}  ({len(agg_df)} aggregate rows)")
    print("\nDone.")


if __name__ == "__main__":
    main()
