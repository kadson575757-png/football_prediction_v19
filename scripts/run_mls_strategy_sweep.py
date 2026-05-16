"""MLS strategy sweep: analyses outputs/backtest_mls.csv after MLS backtesting.
Run this only after completing the MLS validation workflow in DATA_REQUIREMENTS.md.
"""
from __future__ import annotations
import sys
import os
import pandas as pd

BACKTEST_FILE = "outputs/backtest_mls.csv"


def main():
    if not os.path.exists(BACKTEST_FILE):
        print(f"No MLS backtest file found at: {BACKTEST_FILE}")
        print()
        print("Run the MLS validation workflow first:")
        print("  1. fpv19 prepare-data --input data/raw/mls_matches.csv --output data/processed/mls_matches_clean.csv --format native")
        print("  2. fpv19 compare-models --input data/processed/mls_matches_clean.csv --output-dir outputs/model_comparison_mls --test-season 2024")
        print("  3. fpv19 backtest-bets --history data/processed/mls_matches_clean.csv --model outputs/model_comparison_mls/best_model.joblib --output outputs/backtest_mls.csv --report outputs/backtest_mls_report.md --test-season 2024 --min-edge 0.03")
        print()
        print("See docs/DATA_REQUIREMENTS.md for the full workflow.")
        return

    df = pd.read_csv(BACKTEST_FILE)
    value_bets = df[df["value_pick"] != "No Bet"].copy()
    total = len(df)
    n_bets = len(value_bets)

    print(f"=== MLS Strategy Sweep ===")
    print(f"Total backtest rows: {total}")
    print(f"Value bets: {n_bets}")
    if n_bets < 50:
        print("WARNING: fewer than 50 bets — results are not statistically meaningful.")
    print()

    print("ROI by pick type:")
    for pick in ["Home", "Draw", "Away"]:
        sub = value_bets[value_bets["value_pick"] == pick]
        if len(sub) == 0:
            continue
        roi = sub["profit"].sum() / len(sub) * 100
        warn = " [LOW SAMPLE < 50]" if len(sub) < 50 else ""
        print(f"  {pick}: {len(sub)} bets, ROI {roi:.2f}%{warn}")

    print()
    print("ROI by min_edge threshold:")
    for threshold in [0.02, 0.03, 0.04, 0.05]:
        sub = value_bets[value_bets["value_edge"] >= threshold]
        if len(sub) == 0:
            print(f"  edge >= {threshold:.2f}: no bets")
            continue
        roi = sub["profit"].sum() / len(sub) * 100
        warn = " [LOW SAMPLE < 50]" if len(sub) < 50 else ""
        print(f"  edge >= {threshold:.2f}: {len(sub)} bets, ROI {roi:.2f}%{warn}")

    print()
    print("DISCLAIMER: MLS is not yet validated for paper testing.")
    print("Review these results carefully before using any MLS strategy.")


if __name__ == "__main__":
    main()
