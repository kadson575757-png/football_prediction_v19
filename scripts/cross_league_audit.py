# -*- coding: utf-8 -*-
"""Cross-league strategy mining audit.

Reads all available backtest CSVs and mines for robust candidate strategies
across league / pick-type / edge-threshold / odds-band dimensions.

Diagnostic only - no betting recommendations.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── helpers ──────────────────────────────────────────────────────────────────

def compute_stats(sub: pd.DataFrame, stake_col: str = "profit") -> dict[str, Any]:
    """Given a subset of bet rows, compute key stats."""
    n = len(sub)
    if n == 0:
        return {}
    profit = sub["profit"].sum()
    roi = profit / n * 100
    hit = (sub["profit"] > 0).sum()
    hit_rate = hit / n * 100

    # avg odds of the picked selection
    avg_odds = sub.apply(
        lambda r: r["odds_home"] if r["value_pick"] == "Home"
        else r["odds_draw"] if r["value_pick"] == "Draw"
        else r["odds_away"],
        axis=1,
    ).mean()

    # max drawdown via cumulative profit sequence
    cum = sub["profit"].cumsum().values
    running_max = np.maximum.accumulate(np.concatenate([[0], cum[:-1]]))
    dd = (cum - running_max).min()

    # dependency on top-3 wins
    top3 = sub[sub["profit"] > 0].nlargest(3, "profit")["profit"].sum()
    profit_ex_top3 = profit - top3
    roi_ex_top3 = profit_ex_top3 / n * 100

    return {
        "n": n,
        "profit": round(profit, 2),
        "roi": round(roi, 1),
        "hit_rate": round(hit_rate, 1),
        "hit": int(hit),
        "avg_odds": round(avg_odds, 2),
        "max_dd": round(dd, 2),
        "top3_wins": round(top3, 2),
        "profit_ex_top3": round(profit_ex_top3, 2),
        "roi_ex_top3": round(roi_ex_top3, 1),
    }


def filter_bets(df: pd.DataFrame, pick: str | None = None,
                min_edge: float = 0.0, max_odds: float = 999,
                min_odds: float = 1.0) -> pd.DataFrame:
    """Return placed bets matching pick/edge/odds criteria."""
    sub = df[df["stake"] > 0].copy()
    if pick:
        sub = sub[sub["value_pick"] == pick]
    sub = sub[sub["value_edge"] >= min_edge]
    if pick == "Home":
        sub = sub[(sub["odds_home"] >= min_odds) & (sub["odds_home"] <= max_odds)]
    elif pick == "Draw":
        sub = sub[(sub["odds_draw"] >= min_odds) & (sub["odds_draw"] <= max_odds)]
    elif pick == "Away":
        sub = sub[(sub["odds_away"] >= min_odds) & (sub["odds_away"] <= max_odds)]
    return sub


def hard_reject(stats: dict) -> str | None:
    """Return rejection reason string or None if candidate passes."""
    n = stats.get("n", 0)
    if n < 50:
        return f"n={n} < 50"
    profit = stats.get("profit", 0)
    dd = stats.get("max_dd", 0)
    if dd < 0 and abs(dd) > abs(profit) * 2 and profit > 0:
        return f"drawdown ({dd:.1f}) > 2x profit ({profit:.1f})"
    if profit <= 0:
        return f"profit <= 0 ({profit:.2f})"
    ex3 = stats.get("profit_ex_top3", 0)
    if ex3 <= 0 and profit > 0:
        return f"profit disappears ex-top3 (ex3={ex3:.2f})"
    return None


# ── load backtest files ───────────────────────────────────────────────────────

FILES: dict[str, str] = {
    "MLS_2024_full":   "outputs/backtest_mls_2024.csv",   # 2024+2025 OOS rows
    "MLS_2025_only":   "outputs/backtest_mls_2025.csv",   # 2025 strict OOS only
    "Top5_2023":       "outputs/backtest_top5_2023.csv",  # 5 leagues, 1 season
    "D2_2024":         "outputs/backtest_d2_2024.csv",
    "Eredivisie_2024": "outputs/backtest_eredivisie_2024.csv",
}

dfs: dict[str, pd.DataFrame] = {}
for name, path in FILES.items():
    p = Path(path)
    if not p.exists():
        print(f"WARNING: {path} not found, skipping")
        continue
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df["_source"] = name
    dfs[name] = df

# Split MLS_2024 into two calendar-year seasons for cross-season checks
mls24 = dfs.get("MLS_2024_full", pd.DataFrame())
if not mls24.empty:
    dfs["MLS_2024_yr2024"] = mls24[mls24["date"].dt.year == 2024].copy()
    dfs["MLS_2024_yr2025"] = mls24[mls24["date"].dt.year == 2025].copy()

print("=== Loaded datasets ===")
for name, df in dfs.items():
    bets = (df["stake"] > 0).sum() if "stake" in df.columns else 0
    league_s = df["league"].unique().tolist() if "league" in df.columns else []
    print(f"  {name}: rows={len(df)}, bets={bets}, leagues={league_s}")
print()


# ── dimension sweep ───────────────────────────────────────────────────────────

EDGE_THRESHOLDS = [0.03, 0.04, 0.05, 0.06, 0.07, 0.10]
PICKS = ["Home", "Draw", "Away"]

# Define odds bands for each pick type (for narrowed searches)
ODDS_BANDS: dict[str, list[tuple[float, float]]] = {
    "Home":  [(1.0, 2.0), (1.5, 2.5), (2.0, 4.0), (1.0, 999)],
    "Draw":  [(3.0, 5.0), (3.5, 6.0), (3.0, 999)],
    "Away":  [(1.5, 3.0), (2.0, 4.0), (3.0, 6.0), (1.5, 999)],
}

candidates: list[dict] = []

# ── 1. Primary sweep: source x pick x edge ───────────────────────────────────

for src_name, df in dfs.items():
    if df.empty or "stake" not in df.columns:
        continue
    leagues = df["league"].unique().tolist()
    league_label = leagues[0] if len(leagues) == 1 else "+".join(sorted(set(str(x) for x in leagues)))

    for pick in PICKS:
        for edge in EDGE_THRESHOLDS:
            sub = filter_bets(df, pick=pick, min_edge=edge)
            if len(sub) == 0:
                continue
            st = compute_stats(sub)
            reject = hard_reject(st)
            candidates.append({
                "source": src_name,
                "league": league_label,
                "pick": pick,
                "min_edge": edge,
                "odds_band": "any",
                **st,
                "reject": reject,
            })


# ── 2. Odds-band sweep on full datasets ──────────────────────────────────────

PRIMARY_SOURCES = ["MLS_2024_full", "MLS_2025_only", "Top5_2023", "D2_2024", "Eredivisie_2024"]
for src_name in PRIMARY_SOURCES:
    df = dfs.get(src_name)
    if df is None or df.empty:
        continue
    leagues = df["league"].unique().tolist()
    league_label = leagues[0] if len(leagues) == 1 else "+".join(sorted(set(str(x) for x in leagues)))

    for pick in PICKS:
        for lo, hi in ODDS_BANDS.get(pick, []):
            for edge in [0.03, 0.04, 0.05]:
                sub = filter_bets(df, pick=pick, min_edge=edge, min_odds=lo, max_odds=hi)
                if len(sub) == 0:
                    continue
                st = compute_stats(sub)
                reject = hard_reject(st)
                label = f"{lo:.1f}-{hi:.0f}" if hi < 900 else f"{lo:.1f}+"
                candidates.append({
                    "source": src_name,
                    "league": league_label,
                    "pick": pick,
                    "min_edge": edge,
                    "odds_band": label,
                    **st,
                    "reject": reject,
                })


# ── 3. Top-5 per-league breakdown ─────────────────────────────────────────────

top5 = dfs.get("Top5_2023")
if top5 is not None and not top5.empty:
    for league in top5["league"].unique():
        sub_df = top5[top5["league"] == league].copy()
        for pick in PICKS:
            for edge in [0.03, 0.04, 0.05, 0.06]:
                sub = filter_bets(sub_df, pick=pick, min_edge=edge)
                if len(sub) == 0:
                    continue
                st = compute_stats(sub)
                reject = hard_reject(st)
                candidates.append({
                    "source": "Top5_2023",
                    "league": league,
                    "pick": pick,
                    "min_edge": edge,
                    "odds_band": "any",
                    **st,
                    "reject": reject,
                })


# ── 4. MLS cross-season checks ────────────────────────────────────────────────

for pick in PICKS:
    for edge in [0.03, 0.04, 0.05, 0.06]:
        sub_2024 = filter_bets(dfs.get("MLS_2024_yr2024", pd.DataFrame()), pick=pick, min_edge=edge)
        sub_2025 = filter_bets(dfs.get("MLS_2024_yr2025", pd.DataFrame()), pick=pick, min_edge=edge)
        if len(sub_2024) == 0 or len(sub_2025) == 0:
            continue
        for yr, sub in [("2024", sub_2024), ("2025", sub_2025)]:
            st = compute_stats(sub)
            reject = hard_reject(st)
            candidates.append({
                "source": f"MLS_yr{yr}",
                "league": "MLS",
                "pick": pick,
                "min_edge": edge,
                "odds_band": "any",
                **st,
                "reject": reject,
            })


# ── build result dataframe ────────────────────────────────────────────────────

cdf = pd.DataFrame(candidates)
cdf = cdf.drop_duplicates(subset=["source", "league", "pick", "min_edge", "odds_band"])
cdf = cdf.sort_values(["reject", "roi"], ascending=[True, False], na_position="last")

passed = cdf[cdf["reject"].isna()].copy()
rejected = cdf[cdf["reject"].notna()].copy()

print(f"Total candidate rows: {len(cdf)}")
print(f"  Passed hard filters: {len(passed)}")
print(f"  Rejected: {len(rejected)}")
print()


# ── print passed candidates ───────────────────────────────────────────────────

print("=" * 80)
print("PASSED candidates (sorted by ROI desc):")
print("=" * 80)
cols_show = ["source", "league", "pick", "min_edge", "odds_band", "n", "profit", "roi",
             "hit_rate", "avg_odds", "max_dd", "profit_ex_top3", "roi_ex_top3"]
if not passed.empty:
    for _, row in passed.sort_values("roi", ascending=False).iterrows():
        print(f"\n  [{row['source']}] {row['league']} | {row['pick']} | edge>={row['min_edge']:.2f} | odds={row['odds_band']}")
        print(f"    n={row['n']}, profit={row['profit']:.2f}, ROI={row['roi']:.1f}%, hit={row['hit_rate']:.1f}%")
        print(f"    avg_odds={row['avg_odds']:.2f}, max_dd={row['max_dd']:.2f}")
        print(f"    ex-top3: profit={row['profit_ex_top3']:.2f}, ROI={row['roi_ex_top3']:.1f}%")
else:
    print("  None")

print()
print("=" * 80)
print("TOP REJECTED candidates (positive ROI, n>=20, sorted by ROI):")
print("=" * 80)
near_miss = rejected[rejected["roi"] > 0].sort_values("roi", ascending=False).head(20)
for _, row in near_miss.iterrows():
    print(f"\n  [{row['source']}] {row['league']} | {row['pick']} | edge>={row['min_edge']:.2f} | odds={row['odds_band']}")
    print(f"    n={row['n']}, profit={row['profit']:.2f}, ROI={row['roi']:.1f}%, hit={row['hit_rate']:.1f}%")
    print(f"    avg_odds={row['avg_odds']:.2f}, max_dd={row['max_dd']:.2f}")
    print(f"    ex-top3: profit={row['profit_ex_top3']:.2f}, ROI={row['roi_ex_top3']:.1f}%")
    print(f"    REJECTED: {row['reject']}")
