"""Diagnostic audit: does lower control_score correlate with higher total goals?

Reads MLS historical match data, runs feature engineering + model predictions,
extracts control_score + chaos_score per match, then aggregates by bucket.

Output:
  outputs/diagnostics/mls_control_goals_audit.csv   -- row-level detail
  outputs/diagnostics/mls_control_goals_summary.md  -- bucketed summary

DIAGNOSTIC ONLY — no betting recommendations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from football_prediction_v19.data import load_matches
from football_prediction_v19.features import build_features
from football_prediction_v19.model import load_model, predict_feature_rows
from football_prediction_v19.rules_v19 import assess_prediction

HISTORY_FILE = "data/processed/mls_matches_clean_with_odds.csv"
MODEL_FILE = "outputs/model_comparison_mls_2025/best_model.joblib"
OUT_DIR = Path("outputs/diagnostics")
AUDIT_CSV = OUT_DIR / "mls_control_goals_audit.csv"
SUMMARY_MD = OUT_DIR / "mls_control_goals_summary.md"

BUCKETS = [
    ("control < 4.0",      lambda c: c < 4.0),
    ("4.0 <= control < 5.5", lambda c: (c >= 4.0) & (c < 5.5)),
    ("5.5 <= control < 7.0", lambda c: (c >= 5.5) & (c < 7.0)),
    ("control >= 7.0",     lambda c: c >= 7.0),
]

TEST_SEASONS = [2024, 2025]


def build_audit_rows() -> pd.DataFrame:
    print("Loading history and building features...")
    raw = load_matches(HISTORY_FILE)
    table = build_features(raw).sort_values("date").reset_index(drop=True)

    print("Loading model and predicting...")
    bundle = load_model(MODEL_FILE)
    pred_rows = predict_feature_rows(bundle, table)

    print(f"Running assess_prediction on {len(pred_rows)} rows...")
    records = []
    for i, (_, row) in enumerate(pred_rows.iterrows()):
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(pred_rows)}")
        probs = {"H": row["prob_home"], "D": row["prob_draw"], "A": row["prob_away"]}
        assessment = assess_prediction(row, probs)
        control = assessment["control_model_score"]
        chaos = assessment["chaos_score"]
        home_g = float(row["home_goals"])
        away_g = float(row["away_goals"])
        total = home_g + away_g
        records.append({
            "date": pd.to_datetime(row["date"]).date().isoformat(),
            "season": int(row["season_start"]) if "season_start" in row.index else None,
            "league": row.get("league", "MLS"),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "result": str(row["result"]),
            "home_goals": home_g,
            "away_goals": away_g,
            "total_goals": total,
            "prob_home": round(float(row["prob_home"]), 4),
            "prob_draw": round(float(row["prob_draw"]), 4),
            "prob_away": round(float(row["prob_away"]), 4),
            "control_score": control,
            "chaos_score": chaos,
            "over_1_5": int(total > 1.5),
            "over_2_5": int(total > 2.5),
            "over_3_5": int(total > 3.5),
            "btts": int(home_g > 0 and away_g > 0),
            "home_win": int(row["result"] == "H"),
            "draw": int(row["result"] == "D"),
            "away_win": int(row["result"] == "A"),
        })
    return pd.DataFrame(records)


def bucket_stats(df: pd.DataFrame, label: str) -> dict:
    n = len(df)
    if n == 0:
        return {k: None for k in [
            "season", "bucket", "matches", "avg_total_goals", "median_total_goals",
            "over_1_5_pct", "over_2_5_pct", "over_3_5_pct", "btts_pct",
            "home_win_pct", "draw_pct", "away_win_pct",
            "avg_control", "avg_chaos",
        ]}
    return {
        "season": label.split("|")[0].strip(),
        "bucket": label.split("|")[1].strip() if "|" in label else label,
        "matches": n,
        "avg_total_goals": round(df["total_goals"].mean(), 3),
        "median_total_goals": round(df["total_goals"].median(), 2),
        "over_1_5_pct": round(df["over_1_5"].mean() * 100, 1),
        "over_2_5_pct": round(df["over_2_5"].mean() * 100, 1),
        "over_3_5_pct": round(df["over_3_5"].mean() * 100, 1),
        "btts_pct": round(df["btts"].mean() * 100, 1),
        "home_win_pct": round(df["home_win"].mean() * 100, 1),
        "draw_pct": round(df["draw"].mean() * 100, 1),
        "away_win_pct": round(df["away_win"].mean() * 100, 1),
        "avg_control": round(df["control_score"].mean(), 3),
        "avg_chaos": round(df["chaos_score"].mean(), 3),
    }


def correlation_section(df: pd.DataFrame, season_label: str) -> list[str]:
    lines = [f"### Correlations — {season_label}", ""]
    for target, target_label in [("total_goals", "Total Goals")]:
        for predictor, pred_label in [("control_score", "Control Score"), ("chaos_score", "Chaos Score")]:
            clean = df[[predictor, target]].dropna()
            if len(clean) < 10:
                lines.append(f"- {pred_label} vs {target_label}: insufficient data")
                continue
            pearson_r, pearson_p = stats.pearsonr(clean[predictor], clean[target])
            spearman_r, spearman_p = stats.spearmanr(clean[predictor], clean[target])
            lines.append(
                f"- **{pred_label} vs {target_label}**: "
                f"Pearson r={pearson_r:+.3f} (p={pearson_p:.4f}), "
                f"Spearman ρ={spearman_r:+.3f} (p={spearman_p:.4f})"
            )
    lines.append("")
    return lines


def build_summary_md(audit: pd.DataFrame) -> str:
    lines = [
        "# MLS Control Score vs Total Goals — Diagnostic Audit",
        "",
        "> DIAGNOSTIC ONLY — no betting recommendations.",
        "> Paper-test rules at end of document, if signal is strong enough.",
        "",
    ]

    all_rows = []
    for season_filter, season_label in [(None, "All seasons")] + [(s, str(s)) for s in TEST_SEASONS]:
        if season_filter is not None:
            sub = audit[audit["season"] == season_filter].copy()
        else:
            sub = audit.copy()

        if len(sub) == 0:
            continue

        lines.append(f"## Season: {season_label} (n={len(sub)})")
        lines.append("")
        lines.append("| Bucket | Matches | Avg Goals | Median | O1.5% | O2.5% | O3.5% | BTTS% | H% | D% | A% | Avg Control | Avg Chaos |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

        for bname, bfn in BUCKETS:
            bmask = bfn(sub["control_score"])
            bdf = sub[bmask]
            lbl = f"{season_label} | {bname}"
            s = bucket_stats(bdf, lbl)
            if s["matches"] == 0 or s["matches"] is None:
                lines.append(f"| {bname} | 0 | — | — | — | — | — | — | — | — | — | — | — |")
                continue
            lines.append(
                f"| {bname} | {s['matches']} | {s['avg_total_goals']} | {s['median_total_goals']} | "
                f"{s['over_1_5_pct']}% | {s['over_2_5_pct']}% | {s['over_3_5_pct']}% | {s['btts_pct']}% | "
                f"{s['home_win_pct']}% | {s['draw_pct']}% | {s['away_win_pct']}% | "
                f"{s['avg_control']} | {s['avg_chaos']} |"
            )
            all_rows.append(s)

        lines.append("")
        lines += correlation_section(sub, season_label)

    # Today's 4 games reference
    lines += [
        "## Today's 4 Games (2026-05-17) — Reference",
        "",
        "| Match | Control | Chaos | Total Goals |",
        "|---|---:|---:|---:|",
        "| Seattle vs LA Galaxy | 7.56 | 2.00 | 2 |",
        "| Real Salt Lake vs Colorado | 6.52 | 3.05 | 3 |",
        "| San Diego vs Cincinnati | 5.12 | 4.00 | 6 |",
        "| San Jose vs Dallas | 3.60 | 5.47 | 5 |",
        "",
    ]

    # Paper test proposal
    lines += [
        "## Paper-Test Proposal (if signal validated)",
        "",
        "> Only activate if Over 2.5 in low-control bucket is ≥ 55% AND repeats across both 2024 and 2025.",
        "",
        "**Proposed rule (diagnostic paper-test only):**",
        "- League: MLS",
        "- Condition: control_score < 5.5",
        "- Market: Over 2.5 goals",
        "- Stake: 1.0 unit flat",
        "- Minimum 50 tracked bets before evaluation",
        "- Stop/review if drawdown > 15 units",
        "- NO LIVE BETTING — paper track only",
        "",
        "> Odds data for Over 2.5 markets not currently in dataset.",
        "> ROI cannot be computed without those odds.",
        "> Signal strength assessment is based on hit rate vs market implied probability only.",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    audit = build_audit_rows()

    # Keep only MLS rows from the test seasons for the core analysis,
    # but also produce an all-seasons view
    mls = audit[audit["league"].str.strip() == "MLS"].copy()
    print(f"\nTotal MLS rows: {len(mls)}")
    for s in TEST_SEASONS:
        print(f"  Season {s}: {len(mls[mls['season'] == s])} rows")

    audit.to_csv(AUDIT_CSV, index=False)
    print(f"Saved row-level audit: {AUDIT_CSV}")

    summary = build_summary_md(mls)
    SUMMARY_MD.write_text(summary, encoding="utf-8")
    print(f"Saved summary: {SUMMARY_MD}")

    # Print compact console summary
    print("\n" + "="*70)
    print("CONTROL BUCKET SUMMARY (all MLS test seasons combined)")
    print("="*70)
    print(f"{'Bucket':<26} {'N':>5} {'AvgG':>6} {'O2.5%':>7} {'O3.5%':>7} {'H%':>6} {'D%':>6} {'A%':>6}")
    print("-"*70)
    for bname, bfn in BUCKETS:
        bmask = bfn(mls["control_score"])
        bdf = mls[bmask]
        if len(bdf) == 0:
            print(f"  {bname:<24} {'0':>5}")
            continue
        print(
            f"  {bname:<24} {len(bdf):>5} "
            f"{bdf['total_goals'].mean():>6.2f} "
            f"{bdf['over_2_5'].mean()*100:>6.1f}% "
            f"{bdf['over_3_5'].mean()*100:>6.1f}% "
            f"{bdf['home_win'].mean()*100:>5.1f}% "
            f"{bdf['draw'].mean()*100:>5.1f}% "
            f"{bdf['away_win'].mean()*100:>5.1f}%"
        )

    print()
    print("CORRELATIONS (all MLS, control_score vs total_goals):")
    clean = mls[["control_score", "chaos_score", "total_goals"]].dropna()
    for predictor, plabel in [("control_score", "Control"), ("chaos_score", "Chaos")]:
        pr, pp = stats.pearsonr(clean[predictor], clean[target := "total_goals"])
        sr, sp = stats.spearmanr(clean[predictor], clean[target])
        sig = "***" if pp < 0.001 else ("**" if pp < 0.01 else ("*" if pp < 0.05 else ""))
        print(f"  {plabel:10s} vs Total Goals: Pearson r={pr:+.3f}{sig} (p={pp:.4f}), Spearman r={sr:+.3f}")

    print()
    print("PER-SEASON O2.5 IN LOWEST BUCKET (control < 4.0):")
    for s in TEST_SEASONS:
        ssub = mls[mls["season"] == s]
        blow = ssub[ssub["control_score"] < 4.0]
        if len(blow) == 0:
            print(f"  {s}: 0 rows")
        else:
            print(f"  {s}: {len(blow)} matches, O2.5={blow['over_2_5'].mean()*100:.1f}%, O3.5={blow['over_3_5'].mean()*100:.1f}%, avg goals={blow['total_goals'].mean():.2f}")

    print()
    print("PER-SEASON O2.5 IN LOW-MEDIUM BUCKET (4.0 <= control < 5.5):")
    for s in TEST_SEASONS:
        ssub = mls[mls["season"] == s]
        blow = ssub[(ssub["control_score"] >= 4.0) & (ssub["control_score"] < 5.5)]
        if len(blow) == 0:
            print(f"  {s}: 0 rows")
        else:
            print(f"  {s}: {len(blow)} matches, O2.5={blow['over_2_5'].mean()*100:.1f}%, O3.5={blow['over_3_5'].mean()*100:.1f}%, avg goals={blow['total_goals'].mean():.2f}")


if __name__ == "__main__":
    main()
