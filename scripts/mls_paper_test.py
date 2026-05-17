"""Generate MLS Away paper-test candidates from predict-fixtures output or backtest CSV.

Usage — upcoming fixtures (PENDING):
    python scripts/mls_paper_test.py \\
        --input outputs/pipeline_predictions.csv \\
        --mode pending \\
        --candidates outputs/paper_test/mls_away_candidates.csv \\
        --ledger outputs/paper_test/mls_away_ledger.csv

Usage — settle historical backtest rows into ledger:
    python scripts/mls_paper_test.py \\
        --input outputs/backtest_mls_2025.csv \\
        --mode settled \\
        --candidates outputs/paper_test/mls_away_candidates.csv \\
        --ledger outputs/paper_test/mls_away_ledger.csv

Filters applied:
  - league == MLS
  - value_pick == Away
  - edge_away >= 0.04  (--min-edge)
  - control_score >= 7.0  (--min-control)
  - chaos_score <= 7.0  (--max-chaos)
  - odds_away present and > 1
  - Stake is always 1.0 unit (flat)
  - Home and Draw picks are always excluded

PAPER TEST ONLY. See docs/MLS_PAPER_TEST.md.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from football_prediction_v19.paper_test.mls_away_filter import (
    MIN_CONTROL,
    MIN_EDGE,
    MAX_CHAOS,
    append_candidates,
    filter_candidates,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="MLS Away paper-test candidate filter")
    parser.add_argument("--input", required=True, help="predict-fixtures CSV or backtest CSV")
    parser.add_argument(
        "--mode",
        choices=["pending", "settled"],
        default="pending",
        help="'pending' for upcoming fixtures, 'settled' for historical backtest rows",
    )
    parser.add_argument("--candidates", required=True, help="Output: mls_away_candidates.csv")
    parser.add_argument("--ledger", required=True, help="Output: mls_away_ledger.csv (append-safe)")
    parser.add_argument("--min-edge", type=float, default=MIN_EDGE)
    parser.add_argument("--min-control", type=float, default=MIN_CONTROL)
    parser.add_argument("--max-chaos", type=float, default=MAX_CHAOS)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    status = "PENDING" if args.mode == "pending" else "SETTLED"
    candidates = filter_candidates(
        df,
        min_edge=args.min_edge,
        min_control=args.min_control,
        max_chaos=args.max_chaos,
        status=status,
    )

    candidates_path = Path(args.candidates)
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(candidates_path, index=False)

    ledger = append_candidates(candidates, args.ledger)

    print(f"MLS Away paper-test candidates")
    print(f"  Input          : {args.input}")
    print(f"  Mode           : {status}")
    print(f"  Min edge       : {args.min_edge}")
    print(f"  Min control    : {args.min_control}")
    print(f"  Max chaos      : {args.max_chaos}")
    print(f"  Candidates     : {len(candidates)} rows -> {candidates_path}")
    print(f"  Ledger         : {len(ledger)} total rows -> {args.ledger}")

    if len(candidates) == 0:
        print("  [No candidates passed all gates]")
    else:
        print()
        print(candidates[["date", "home_team", "away_team", "odds_away", "edge", "control_score", "status"]].to_string(index=False))


if __name__ == "__main__":
    main()
