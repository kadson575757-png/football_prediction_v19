# -*- coding: utf-8 -*-
"""Deep dive: cross-season stability, benchmark comparison, final ranking."""
from __future__ import annotations
import numpy as np
import pandas as pd

def compute_stats(sub):
    n = len(sub)
    if n == 0:
        return {}
    profit = sub["profit"].sum()
    roi = profit / n * 100
    hit = (sub["profit"] > 0).sum()
    avg_odds = sub.apply(
        lambda r: r["odds_home"] if r["value_pick"] == "Home"
        else r["odds_draw"] if r["value_pick"] == "Draw"
        else r["odds_away"], axis=1).mean()
    cum = sub["profit"].cumsum().values
    rm = np.maximum.accumulate(np.concatenate([[0], cum[:-1]]))
    dd = (cum - rm).min()
    top3 = sub[sub["profit"] > 0].nlargest(3, "profit")["profit"].sum()
    return {
        "n": n, "profit": round(profit, 2), "roi": round(roi, 1),
        "hit": int(hit), "hit_rate": round(hit / n * 100, 1),
        "avg_odds": round(avg_odds, 2), "max_dd": round(dd, 2),
        "top3_wins": round(top3, 2),
        "profit_ex_top3": round(profit - top3, 2),
        "roi_ex_top3": round((profit - top3) / n * 100, 1),
    }

def pick_bets(df, pick, min_edge=0.0, min_odds=1.0, max_odds=999):
    sub = df[df["stake"] > 0].copy()
    sub = sub[sub["value_pick"] == pick]
    sub = sub[sub["value_edge"] >= min_edge]
    odds_col = {"Home": "odds_home", "Draw": "odds_draw", "Away": "odds_away"}[pick]
    sub = sub[(sub[odds_col] >= min_odds) & (sub[odds_col] <= max_odds)]
    return sub

# Load all files
mls24 = pd.read_csv("outputs/backtest_mls_2024.csv")
mls25 = pd.read_csv("outputs/backtest_mls_2025.csv")
top5  = pd.read_csv("outputs/backtest_top5_2023.csv")
d2    = pd.read_csv("outputs/backtest_d2_2024.csv")
n1    = pd.read_csv("outputs/backtest_eredivisie_2024.csv")

for df in [mls24, mls25, top5, d2, n1]:
    df["date"] = pd.to_datetime(df["date"])

mls24_2024 = mls24[mls24["date"].dt.year == 2024].copy()
mls24_2025 = mls24[mls24["date"].dt.year == 2025].copy()

SEP = "=" * 72


# ── SECTION 1: MLS Away benchmark ────────────────────────────────────────────
print(SEP)
print("SECTION 1: MLS Away — the benchmark strategy")
print(SEP)

print("\nMLS Away edge>=0.04, all available slices:")
for name, df in [
    ("MLS_2024_full (both years)", mls24),
    ("MLS_2024_yr2024 (2024 only)", mls24_2024),
    ("MLS_2024_yr2025 (2025 in 2024 model)", mls24_2025),
    ("MLS_2025_only  (2025 strict OOS)", mls25),
]:
    sub = pick_bets(df, "Away", min_edge=0.04)
    if len(sub) == 0:
        print(f"  {name}: 0 bets")
        continue
    st = compute_stats(sub)
    print(f"  {name}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, avg_odds={st['avg_odds']:.2f},"
          f" ex-top3 ROI={st['roi_ex_top3']:.1f}%, max_dd={st['max_dd']:.2f}")

print("\nMLS Away edge threshold sweep — MLS_2025_only (strict OOS):")
for edge in [0.03, 0.04, 0.05, 0.06, 0.07, 0.10]:
    sub = pick_bets(mls25, "Away", min_edge=edge)
    if len(sub) == 0: continue
    st = compute_stats(sub)
    print(f"  edge>={edge:.2f}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, ex-top3={st['roi_ex_top3']:.1f}%, dd={st['max_dd']:.2f}")

print("\nMLS Away edge>=0.04 — year-by-year cross-season consistency:")
for yr_name, df in [("2024 (yr2024)", mls24_2024), ("2025-in-2024-model (yr2025)", mls24_2025),
                    ("2025 strict OOS", mls25)]:
    sub = pick_bets(df, "Away", min_edge=0.04)
    st = compute_stats(sub)
    if st:
        print(f"  {yr_name}: n={st['n']}, ROI={st['roi']:.1f}%, hit={st['hit_rate']:.1f}%,"
              f" ex-top3 ROI={st['roi_ex_top3']:.1f}%")

# ── SECTION 2: MLS Away odds-band stability ───────────────────────────────────
print(f"\n{SEP}")
print("SECTION 2: MLS Away odds-band breakdown (MLS_2025_only, edge>=0.04)")
print(SEP)
bands = [(1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 6.0), (6.0, 999)]
for lo, hi in bands:
    sub = pick_bets(mls25, "Away", min_edge=0.04, min_odds=lo, max_odds=hi)
    if len(sub) == 0: continue
    st = compute_stats(sub)
    label = f"{lo:.1f}-{hi:.0f}" if hi < 900 else f"{lo:.1f}+"
    print(f"  odds {label}: n={st['n']}, ROI={st['roi']:.1f}%, hit={st['hit_rate']:.1f}%,"
          f" avg_odds={st['avg_odds']:.2f}, ex-top3={st['roi_ex_top3']:.1f}%")

# ── SECTION 3: Top-5 Draw signal deep dive ────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 3: Top-5 combined Draw signal")
print(SEP)

print("\nTop-5 combined Draw, edge>=0.03, odds bands:")
draw_bets = pick_bets(top5, "Draw", min_edge=0.03)
for lo, hi in [(3.0, 4.0), (3.5, 5.0), (4.0, 6.0), (3.0, 5.0), (3.0, 6.0), (3.5, 999)]:
    sub = draw_bets[(draw_bets["odds_draw"] >= lo) & (draw_bets["odds_draw"] <= hi)]
    if len(sub) < 10: continue
    st = compute_stats(sub)
    label = f"{lo:.1f}-{hi:.0f}" if hi < 900 else f"{lo:.1f}+"
    print(f"  odds {label}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, avg_odds={st['avg_odds']:.2f}, ex-top3={st['roi_ex_top3']:.1f}%,"
          f" dd={st['max_dd']:.2f}")

print("\nTop-5 Draw per-league breakdown (edge>=0.03, odds 3.5-6):")
for league in sorted(top5["league"].unique()):
    sub_l = top5[top5["league"] == league]
    sub = pick_bets(sub_l, "Draw", min_edge=0.03)
    sub = sub[(sub["odds_draw"] >= 3.5) & (sub["odds_draw"] <= 6.0)]
    if len(sub) == 0: continue
    st = compute_stats(sub)
    print(f"  {league}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, avg_odds={st['avg_odds']:.2f}, ex-top3={st['roi_ex_top3']:.1f}%")

print("\nTop-5 Draw per-league (edge>=0.03, any odds):")
for league in sorted(top5["league"].unique()):
    sub_l = top5[top5["league"] == league]
    sub = pick_bets(sub_l, "Draw", min_edge=0.03)
    if len(sub) == 0: continue
    st = compute_stats(sub)
    print(f"  {league}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, avg_odds={st['avg_odds']:.2f}, ex-top3={st['roi_ex_top3']:.1f}%")

# Top-5 combined edge sweep
print("\nTop-5 combined Draw edge sweep (any odds):")
for edge in [0.03, 0.04, 0.05, 0.06, 0.07]:
    sub = pick_bets(top5, "Draw", min_edge=edge)
    if len(sub) == 0: continue
    st = compute_stats(sub)
    print(f"  edge>={edge:.2f}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, ex-top3={st['roi_ex_top3']:.1f}%")

# ── SECTION 4: Top-5 Home/Away signals ───────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 4: Top-5 Home and Away signals")
print(SEP)
for pick in ["Home", "Away"]:
    print(f"\nTop-5 {pick} edge sweep:")
    for edge in [0.03, 0.04, 0.05, 0.06, 0.07]:
        sub = pick_bets(top5, pick, min_edge=edge)
        if len(sub) == 0: continue
        st = compute_stats(sub)
        print(f"  edge>={edge:.2f}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
              f" hit={st['hit_rate']:.1f}%, ex-top3={st['roi_ex_top3']:.1f}%")
    print(f"\nTop-5 {pick} per-league (edge>=0.04):")
    for league in sorted(top5["league"].unique()):
        sub = pick_bets(top5[top5["league"] == league], pick, min_edge=0.04)
        if len(sub) == 0: continue
        st = compute_stats(sub)
        print(f"  {league}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
              f" hit={st['hit_rate']:.1f}%, ex-top3={st['roi_ex_top3']:.1f}%")

# ── SECTION 5: D2 Draw signal ────────────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 5: D2 Draw signal (1 OOS season)")
print(SEP)
print("\nD2 Draw edge sweep:")
for edge in [0.03, 0.04, 0.05, 0.06, 0.07]:
    sub = pick_bets(d2, "Draw", min_edge=edge)
    if len(sub) == 0: continue
    st = compute_stats(sub)
    print(f"  edge>={edge:.2f}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, avg_odds={st['avg_odds']:.2f}, ex-top3={st['roi_ex_top3']:.1f}%")

# ── SECTION 6: Eredivisie Home signal ────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 6: Eredivisie Home signal (1 OOS season)")
print(SEP)
for edge in [0.03, 0.04, 0.05, 0.06, 0.07]:
    sub = pick_bets(n1, "Home", min_edge=edge)
    if len(sub) == 0: continue
    st = compute_stats(sub)
    print(f"  edge>={edge:.2f}: n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
          f" hit={st['hit_rate']:.1f}%, avg_odds={st['avg_odds']:.2f}, ex-top3={st['roi_ex_top3']:.1f}%")

# ── SECTION 7: Cross-season check — anything with 2+ positive seasons? ────────
print(f"\n{SEP}")
print("SECTION 7: Cross-season sign consistency check")
print(SEP)
print("\nFor each candidate strategy: sign of ROI across all available OOS seasons")

strategies = [
    ("MLS Away edge>=0.04",  [
        ("MLS 2024 (yr2024)", pick_bets(mls24_2024, "Away", 0.04)),
        ("MLS 2025-in-24mdl", pick_bets(mls24_2025, "Away", 0.04)),
        ("MLS 2025 strict",   pick_bets(mls25, "Away", 0.04)),
    ]),
    ("MLS Away edge>=0.07",  [
        ("MLS 2024 (yr2024)", pick_bets(mls24_2024, "Away", 0.07)),
        ("MLS 2025-in-24mdl", pick_bets(mls24_2025, "Away", 0.07)),
        ("MLS 2025 strict",   pick_bets(mls25, "Away", 0.07)),
    ]),
    ("Top5 Draw edge>=0.03 odds 3.5-6", [
        ("Top5 2023",         pick_bets(top5, "Draw", 0.03).pipe(
            lambda df: df[(df["odds_draw"] >= 3.5) & (df["odds_draw"] <= 6.0)])),
    ]),
    ("D2 Draw edge>=0.03", [
        ("D2 2024",           pick_bets(d2, "Draw", 0.03)),
    ]),
    ("Eredivisie Home edge>=0.03", [
        ("Eredivisie 2024",   pick_bets(n1, "Home", 0.03)),
    ]),
]

for strat_name, slices in strategies:
    print(f"\n  {strat_name}:")
    positive = 0
    for slice_name, sub in slices:
        if len(sub) == 0:
            print(f"    {slice_name}: 0 bets")
            continue
        st = compute_stats(sub)
        sign = "+" if st["roi"] > 0 else "-"
        print(f"    {slice_name}: n={st['n']}, ROI={sign}{abs(st['roi']):.1f}%, ex-top3={st['roi_ex_top3']:.1f}%")
        if st["roi"] > 0:
            positive += 1
    print(f"    -> Positive seasons: {positive}/{len([s for s in slices if len(s[1]) > 0])}")

# ── SECTION 8: Final ranking ──────────────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 8: Final strategy ranking and paper-test comparison")
print(SEP)

# Benchmark: MLS Away edge>=0.04 across 3 OOS slices
bm_2024 = pick_bets(mls24_2024, "Away", 0.04)
bm_2025a = pick_bets(mls24_2025, "Away", 0.04)
bm_2025b = pick_bets(mls25, "Away", 0.04)
bm_all = pd.concat([bm_2024, bm_2025b]).drop_duplicates()

print("\nBENCHMARK — MLS Away edge>=0.04 (combined 2024+2025 OOS bets):")
st = compute_stats(bm_all)
print(f"  n={st['n']}, profit={st['profit']:.2f}, ROI={st['roi']:.1f}%,"
      f" hit={st['hit_rate']:.1f}%, avg_odds={st['avg_odds']:.2f},"
      f" ex-top3 ROI={st['roi_ex_top3']:.1f}%, max_dd={st['max_dd']:.2f}")
print(f"  Positive in: 2024 (ROI={compute_stats(bm_2024)['roi']:.1f}%),"
      f" 2025-strict (ROI={compute_stats(bm_2025b)['roi']:.1f}%)")

print("\nAll passed candidates vs benchmark:")
passed_rows = [
    ("MLS Away edge>=0.10 (2025)", pick_bets(mls25, "Away", 0.10)),
    ("MLS Away edge>=0.07 (2025)", pick_bets(mls25, "Away", 0.07)),
    ("MLS Away edge>=0.06 (2025)", pick_bets(mls25, "Away", 0.06)),
    ("MLS Away edge>=0.04 (2025)", pick_bets(mls25, "Away", 0.04)),
    ("MLS Away edge>=0.04 (combined)", bm_all),
    ("Top5 Draw edge>=0.03 odds 3.5-6", pick_bets(top5, "Draw", 0.03).pipe(
        lambda df: df[(df["odds_draw"] >= 3.5) & (df["odds_draw"] <= 6.0)])),
    ("MLS Away 2.0-4.0 odds edge>=0.04", pick_bets(mls25, "Away", 0.04, 2.0, 4.0)),
    ("MLS Away 1.5-3.0 odds edge>=0.04", pick_bets(mls25, "Away", 0.04, 1.5, 3.0)),
]
for name, sub in passed_rows:
    if len(sub) == 0: continue
    st = compute_stats(sub)
    seasons = "2025only" if "2025" in name and "combined" not in name else "2024+2025"
    print(f"\n  {name}:")
    print(f"    n={st['n']}, ROI={st['roi']:.1f}%, hit={st['hit_rate']:.1f}%,"
          f" avg_odds={st['avg_odds']:.2f}, ex-top3={st['roi_ex_top3']:.1f}%, dd={st['max_dd']:.2f}")
