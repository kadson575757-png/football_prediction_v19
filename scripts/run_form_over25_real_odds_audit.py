# -*- coding: utf-8 -*-
"""Form-pattern Over 2.5 audit using real market odds.

Requires odds_over25 column in the matches file (populated via merge-totals-odds).
Evaluates three form-pattern candidates:
  a) home_gf_high   -- home team scored >= 10 goals in last 5 matches
  b) form_mismatch_H -- home >= 10 pts last-5 AND away <= 5 pts last-5
  c) both_over      -- both teams have >= 60% Over25 rate in last 5 matches

Diagnostic only. No betting recommendations.

Usage:
    python scripts/run_form_over25_real_odds_audit.py --matches data/processed/matches_with_totals.csv
    python scripts/run_form_over25_real_odds_audit.py --matches <file> --window 5 --cold-start 3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Form feature builder (identical logic to form_pattern_audit.py)
# ---------------------------------------------------------------------------

def streak_features(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("date").reset_index(drop=True)
    streak_type = []
    streak_len = []
    for i in range(len(group)):
        if i == 0:
            streak_type.append(None)
            streak_len.append(0)
            continue
        # Walk back from previous match
        outcome = group["outcome"].iloc[i - 1]
        length = 1
        j = i - 2
        while j >= 0 and group["outcome"].iloc[j] == outcome:
            length += 1
            j -= 1
        streak_type.append(outcome)
        streak_len.append(length)
    group["streak_type"] = streak_type
    group["streak_len"] = streak_len
    return group


def rolling_form(df: pd.DataFrame, window: int = 5, cold_start: int = 3) -> pd.DataFrame:
    """Attach pre-match rolling form columns, no look-ahead."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Compute result column if not present
    if "result" not in df.columns:
        def _result(r):
            if r["home_goals"] > r["away_goals"]:
                return "H"
            elif r["home_goals"] == r["away_goals"]:
                return "D"
            return "A"
        df["result"] = df.apply(_result, axis=1)

    # Build long-format team records
    home_records = df[["date", "home_team", "home_goals", "away_goals", "result"]].copy()
    home_records["team"] = home_records["home_team"]
    home_records["gf"] = home_records["home_goals"]
    home_records["ga"] = home_records["away_goals"]
    home_records["is_home"] = 1
    home_records["outcome"] = home_records["result"].map({"H": "W", "D": "D", "A": "L"})
    home_records["pts"] = home_records["outcome"].map({"W": 3, "D": 1, "L": 0})
    home_records["over25"] = (home_records["gf"] + home_records["ga"]) > 2.5

    away_records = df[["date", "home_team", "home_goals", "away_goals", "result"]].copy()
    away_records["team"] = df["away_team"]
    away_records["gf"] = away_records["away_goals"]
    away_records["ga"] = away_records["home_goals"]
    away_records["is_home"] = 0
    away_records["outcome"] = away_records["result"].map({"H": "L", "D": "D", "A": "W"})
    away_records["pts"] = away_records["outcome"].map({"W": 3, "D": 1, "L": 0})
    away_records["over25"] = (away_records["gf"] + away_records["ga"]) > 2.5

    tm = pd.concat([home_records, away_records], ignore_index=True)
    tm = tm.sort_values(["team", "date"]).reset_index(drop=True)

    # Rolling form (shift(1) = no look-ahead)
    def team_rolling(g):
        g = g.sort_values("date")
        g["f_pts"] = g["pts"].shift(1).rolling(window, min_periods=1).sum()
        g["f_gf"] = g["gf"].shift(1).rolling(window, min_periods=1).sum()
        g["f_over25_rate"] = g["over25"].shift(1).rolling(window, min_periods=1).mean()
        g["n_prior"] = g["pts"].shift(1).rolling(window, min_periods=1).count()
        return g

    tm = tm.groupby("team", group_keys=False).apply(team_rolling)

    # Streak features
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        streaks = tm.groupby("team", group_keys=False).apply(streak_features)
    tm["streak_type"] = streaks["streak_type"].values
    tm["streak_len"] = streaks["streak_len"].values

    # Merge back as home_ and away_ prefixes
    home_form = tm[tm["is_home"] == 1][
        ["date", "team", "f_pts", "f_gf", "f_over25_rate", "n_prior", "streak_type", "streak_len"]
    ].rename(columns={
        "team": "home_team",
        "f_pts": "home_f_pts", "f_gf": "home_f_gf",
        "f_over25_rate": "home_f_over25_rate", "n_prior": "home_n_prior",
        "streak_type": "home_streak_type", "streak_len": "home_streak_len",
    })
    away_form = tm[tm["is_home"] == 0][
        ["date", "team", "f_pts", "f_gf", "f_over25_rate", "n_prior", "streak_type", "streak_len"]
    ].rename(columns={
        "team": "away_team",
        "f_pts": "away_f_pts", "f_gf": "away_f_gf",
        "f_over25_rate": "away_f_over25_rate", "n_prior": "away_n_prior",
        "streak_type": "away_streak_type", "streak_len": "away_streak_len",
    })

    df = df.merge(home_form, on=["date", "home_team"], how="left")
    df = df.merge(away_form, on=["date", "away_team"], how="left")

    # Drop cold-start rows
    df = df[
        (df["home_n_prior"] >= cold_start) & (df["away_n_prior"] >= cold_start)
    ].copy()

    return df


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def stats(sub: pd.DataFrame) -> dict | None:
    n = len(sub)
    if n == 0:
        return None
    over25_hit = (sub["total_goals"] > 2.5)
    hit = over25_hit.sum()
    hit_rate = hit / n * 100
    avg_odds = sub["odds_over25"].mean()
    profit = sub.apply(
        lambda r: r["odds_over25"] - 1 if r["total_goals"] > 2.5 else -1, axis=1
    ).sum()
    roi = profit / n * 100

    cum = sub.apply(
        lambda r: r["odds_over25"] - 1 if r["total_goals"] > 2.5 else -1, axis=1
    ).cumsum().values
    rm = np.maximum.accumulate(np.concatenate([[0], cum[:-1]]))
    max_dd = float((cum - rm).min())

    wins = sub[sub["total_goals"] > 2.5]["odds_over25"] - 1
    top3 = wins.nlargest(3).sum() if len(wins) >= 3 else wins.sum()
    profit_ex_top3 = profit - top3
    roi_ex_top3 = profit_ex_top3 / n * 100

    seasons = sorted(sub["date"].dt.year.unique().tolist())
    leagues = sorted(sub["league"].unique().tolist()) if "league" in sub.columns else []

    return {
        "n": n,
        "hit": int(hit),
        "hit_rate": round(hit_rate, 1),
        "avg_odds": round(avg_odds, 3),
        "profit": round(profit, 2),
        "roi": round(roi, 1),
        "max_dd": round(max_dd, 2),
        "top3": round(top3, 2),
        "profit_ex_top3": round(profit_ex_top3, 2),
        "roi_ex_top3": round(roi_ex_top3, 1),
        "seasons": seasons,
        "n_seasons": len(seasons),
        "leagues": leagues,
        "n_leagues": len(leagues),
    }


def print_stats(label: str, s: dict) -> None:
    if s is None:
        print(f"  {label}: no data")
        return
    print(f"  {label}: n={s['n']}, hit={s['hit_rate']}%, avg_odds={s['avg_odds']:.3f}")
    print(f"    profit={s['profit']:.2f}, ROI={s['roi']:.1f}%, max_dd={s['max_dd']:.2f}")
    print(f"    ex-top3: profit={s['profit_ex_top3']:.2f}, ROI={s['roi_ex_top3']:.1f}%")
    print(f"    seasons: {s['seasons']}  leagues: {s['leagues']}")


def per_league_breakdown(sub: pd.DataFrame, label: str) -> None:
    if "league" not in sub.columns or sub.empty:
        return
    print(f"  Per league ({label}):")
    for lg in sorted(sub["league"].unique()):
        sl = sub[sub["league"] == lg]
        s = stats(sl)
        if s:
            flag = ""
            if s["roi"] < 0:
                flag = " [NEGATIVE]"
            print(f"    {lg}: n={s['n']}, hit={s['hit_rate']}%, avg_odds={s['avg_odds']:.3f}, ROI={s['roi']:.1f}%{flag}")


def per_year_breakdown(sub: pd.DataFrame, label: str) -> None:
    if sub.empty:
        return
    print(f"  Per season ({label}):")
    for yr in sorted(sub["date"].dt.year.unique()):
        sy = sub[sub["date"].dt.year == yr]
        s = stats(sy)
        if s:
            flag = " [NEG]" if s["roi"] < 0 else ""
            print(f"    {yr}: n={s['n']}, hit={s['hit_rate']}%, avg_odds={s['avg_odds']:.3f}, ROI={s['roi']:.1f}%{flag}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Form-pattern Over 2.5 audit with real market odds"
    )
    parser.add_argument(
        "--matches", required=True,
        help="Matches CSV with odds_over25 column (use merge-totals-odds first)"
    )
    parser.add_argument("--window", type=int, default=5, help="Rolling form window (default: 5)")
    parser.add_argument("--cold-start", type=int, default=3, dest="cold_start",
                        help="Min prior matches per team before included (default: 3)")
    args = parser.parse_args()

    matches_path = Path(args.matches)
    if not matches_path.exists():
        print(f"ERROR: Matches file not found: {matches_path}", file=sys.stderr)
        print(
            "\nTo create it:\n"
            "  fpv19 import-totals-odds --input my_odds.csv --output totals_normalized.csv\n"
            "  fpv19 merge-totals-odds --matches my_matches.csv --odds totals_normalized.csv "
            "--output matches_with_totals.csv",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"Loading: {matches_path}")
    df = pd.read_csv(matches_path)

    if "odds_over25" not in df.columns or df["odds_over25"].isna().all():
        print(
            "ERROR: odds_over25 column missing or all NaN.\n"
            "Run 'fpv19 merge-totals-odds' to attach real Over 2.5 odds first.",
            file=sys.stderr
        )
        sys.exit(1)

    n_with_odds = df["odds_over25"].notna().sum()
    print(f"  Total rows: {len(df)}, rows with odds_over25: {n_with_odds}")

    if n_with_odds < 50:
        print(
            f"WARNING: Only {n_with_odds} rows have Over 2.5 odds. "
            "Results will not be statistically meaningful (need >= 50)."
        )

    # Build form features
    print(f"\nBuilding form features (window={args.window}, cold_start={args.cold_start})...")
    df["home_goals"] = pd.to_numeric(df.get("home_goals", df.get("FTHG", np.nan)), errors="coerce")
    df["away_goals"] = pd.to_numeric(df.get("away_goals", df.get("FTAG", np.nan)), errors="coerce")
    df = df.dropna(subset=["home_goals", "away_goals"])
    df["total_goals"] = df["home_goals"] + df["away_goals"]
    df["odds_over25"] = pd.to_numeric(df["odds_over25"], errors="coerce")

    df = rolling_form(df, window=args.window, cold_start=args.cold_start)
    print(f"  Rows after form build + cold-start filter: {len(df)}")

    # Restrict to rows that have real Over 2.5 odds
    df_odds = df[df["odds_over25"].notna()].copy()
    print(f"  Rows with odds_over25 for analysis: {len(df_odds)}")

    if df_odds.empty:
        print("\nNo rows with odds_over25 remain after filtering. Nothing to analyse.")
        return

    # Define pattern flags
    df_odds["strong_home_form"] = df_odds["home_f_pts"] >= 10
    df_odds["weak_away_form"] = df_odds["away_f_pts"] <= 5
    df_odds["strong_away_form"] = df_odds["away_f_pts"] >= 10
    df_odds["weak_home_form"] = df_odds["home_f_pts"] <= 5

    df_odds["home_gf_high"] = df_odds["home_f_gf"] >= 10
    df_odds["form_mismatch_H"] = df_odds["strong_home_form"] & df_odds["weak_away_form"]
    df_odds["both_over"] = (
        (df_odds["home_f_over25_rate"] >= 0.6) & (df_odds["away_f_over25_rate"] >= 0.6)
    )

    sep = "-" * 72

    # -------------------------------------------------------------------------
    # Baseline: all rows with odds
    # -------------------------------------------------------------------------
    print(f"\n{sep}")
    print("BASELINE: All matches with real Over 2.5 odds")
    print(sep)
    s_base = stats(df_odds)
    print_stats("All", s_base)
    if s_base:
        print(f"  Note: baseline hit_rate vs implied prob from avg_odds "
              f"({100/s_base['avg_odds']:.1f}%) -> edge estimate: "
              f"{s_base['hit_rate'] - 100/s_base['avg_odds']:.1f}pp")

    # -------------------------------------------------------------------------
    # Candidate a: home_gf_high
    # -------------------------------------------------------------------------
    print(f"\n{sep}")
    print("CANDIDATE a) home_gf_high | Over 2.5")
    print("  home team scored >= 10 goals in last 5 matches")
    print(sep)
    sub_a = df_odds[df_odds["home_gf_high"]].copy()
    s_a = stats(sub_a)
    print_stats("Overall", s_a)
    if s_a:
        implied = 100 / s_a["avg_odds"]
        edge_pp = s_a["hit_rate"] - implied
        print(f"  Implied prob from avg_odds: {implied:.1f}%, actual hit: {s_a['hit_rate']}%")
        print(f"  Edge estimate: {edge_pp:+.1f}pp")
        per_league_breakdown(sub_a, "home_gf_high")
        per_year_breakdown(sub_a, "home_gf_high")

    # -------------------------------------------------------------------------
    # Candidate b: form_mismatch_H
    # -------------------------------------------------------------------------
    print(f"\n{sep}")
    print("CANDIDATE b) form_mismatch_H | Over 2.5")
    print("  home >= 10 pts last-5 AND away <= 5 pts last-5")
    print(sep)
    sub_b = df_odds[df_odds["form_mismatch_H"]].copy()
    s_b = stats(sub_b)
    print_stats("Overall", s_b)
    if s_b:
        implied = 100 / s_b["avg_odds"]
        edge_pp = s_b["hit_rate"] - implied
        print(f"  Implied prob from avg_odds: {implied:.1f}%, actual hit: {s_b['hit_rate']}%")
        print(f"  Edge estimate: {edge_pp:+.1f}pp")
        per_league_breakdown(sub_b, "form_mismatch_H")
        per_year_breakdown(sub_b, "form_mismatch_H")

    # -------------------------------------------------------------------------
    # Candidate c: both_over
    # -------------------------------------------------------------------------
    print(f"\n{sep}")
    print("CANDIDATE c) both_over | Over 2.5")
    print("  both teams have >= 60% Over25 rate in last 5 matches")
    print(sep)
    sub_c = df_odds[df_odds["both_over"]].copy()
    s_c = stats(sub_c)
    print_stats("Overall", s_c)
    if s_c:
        implied = 100 / s_c["avg_odds"]
        edge_pp = s_c["hit_rate"] - implied
        print(f"  Implied prob from avg_odds: {implied:.1f}%, actual hit: {s_c['hit_rate']}%")
        print(f"  Edge estimate: {edge_pp:+.1f}pp")
        per_league_breakdown(sub_c, "both_over")
        per_year_breakdown(sub_c, "both_over")

    # -------------------------------------------------------------------------
    # Odds sensitivity: is the signal priced in?
    # -------------------------------------------------------------------------
    print(f"\n{sep}")
    print("ODDS SENSITIVITY: does the pattern persist across odds bands?")
    print("  (If bookmakers already price in form, high-form games will have")
    print("   lower Over 2.5 odds, and ROI will collapse at low odds bands)")
    print(sep)

    for label, sub in [("home_gf_high", sub_a), ("form_mismatch_H", sub_b), ("both_over", sub_c)]:
        if sub.empty:
            continue
        print(f"\n  {label} -- Over 2.5 ROI by odds band:")
        bands = [(1.55, 1.75), (1.75, 1.88), (1.88, 2.00), (2.00, 2.20), (2.20, 99)]
        for lo, hi in bands:
            band_sub = sub[(sub["odds_over25"] >= lo) & (sub["odds_over25"] < hi)]
            s = stats(band_sub)
            if s and s["n"] >= 10:
                print(f"    odds {lo:.2f}-{hi:.2f}: n={s['n']}, hit={s['hit_rate']}%, ROI={s['roi']:.1f}%")

    # -------------------------------------------------------------------------
    # Hard filter summary
    # -------------------------------------------------------------------------
    print(f"\n{sep}")
    print("HARD FILTER SUMMARY")
    print(sep)
    for label, s in [("home_gf_high", s_a), ("form_mismatch_H", s_b), ("both_over", s_c)]:
        if s is None:
            print(f"  {label}: SKIP (no data)")
            continue
        reasons = []
        if s["n"] < 50:
            reasons.append(f"n={s['n']} < 50")
        if s["roi"] <= 0:
            reasons.append(f"ROI={s['roi']:.1f}% <= 0")
        if s["profit_ex_top3"] <= 0:
            reasons.append(f"profit_ex_top3={s['profit_ex_top3']:.2f} <= 0")
        if s["n_seasons"] < 2:
            reasons.append(f"only {s['n_seasons']} season")
        verdict = "PASS" if not reasons else f"FAIL: {'; '.join(reasons)}"
        print(f"  {label}: {verdict}")

    print(f"\n{sep}")
    print("IMPORTANT NOTES")
    print(sep)
    print("  - ROI calculated with real Over 2.5 odds (not estimated).")
    print("  - Edge estimate = actual hit_rate - implied probability from avg_odds.")
    print("  - A positive edge estimate does NOT guarantee future profitability.")
    print("  - Check the odds sensitivity table: if ROI collapses at lower odds bands,")
    print("    the bookmaker is already pricing in the form signal.")
    print("  - Cross-season consistency (n_seasons positive) is required before paper-test.")
    print("  - This output is diagnostic only. No paper-test rules should be created")
    print("    until cross-season ROI stability is confirmed.")


if __name__ == "__main__":
    main()
