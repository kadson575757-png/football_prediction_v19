"""MLS historical odds smoke test. Requires no internet."""
from __future__ import annotations
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import numpy as np
from pathlib import Path
from football_prediction_v19.importers.historical_odds import import_historical_odds, merge_historical_odds

BASE = Path(__file__).parent.parent

def make_sample_matches():
    return pd.DataFrame({
        "date": ["2025-03-01", "2025-03-08", "2025-03-15", "2025-04-01"],
        "season": [2025, 2025, 2025, 2025],
        "league": ["MLS", "MLS", "MLS", "MLS"],
        "home_team": ["LA Galaxy", "Seattle Sounders", "Atlanta United", "FC Dallas"],
        "away_team": ["Inter Miami", "Portland Timbers", "Orlando City", "Houston Dynamo"],
        "score": ["2-1", "1-1", "2-0", "0-0"],
        "home_xg": [np.nan]*4,
        "away_xg": [np.nan]*4,
        "odds_home": [np.nan]*4,
        "odds_draw": [np.nan]*4,
        "odds_away": [np.nan]*4,
        "venue": [""]*4,
        "referee": [""]*4,
    })

def make_sample_odds():
    return pd.DataFrame({
        "date": ["2025-03-01", "2025-03-08", "2025-03-15"],
        "home_team": ["LA Galaxy", "Seattle Sounders", "Atlanta United"],
        "away_team": ["Inter Miami", "Portland Timbers", "Orlando City"],
        "odds_home": [2.10, 2.30, 1.90],
        "odds_draw": [3.40, 3.20, 3.50],
        "odds_away": [3.60, 3.10, 4.00],
        "bookmaker": ["Bet365", "Bet365", "Bet365"],
        "market": ["h2h", "h2h", "h2h"],
        "updated_at": ["", "", ""],
    })

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        matches_path = tmpdir / "matches.csv"
        odds_raw_path = tmpdir / "odds_raw.csv"
        odds_clean_path = tmpdir / "odds_clean.csv"
        merged_path = tmpdir / "matches_with_odds.csv"

        # Save sample data
        make_sample_matches().to_csv(matches_path, index=False)
        make_sample_odds().to_csv(odds_raw_path, index=False)

        # Import odds
        print("Importing historical odds...")
        odds = import_historical_odds(odds_raw_path, odds_clean_path)
        print(f"  Imported {len(odds)} odds rows")
        print(f"  odds_home non-null: {odds['odds_home'].notna().sum()}")

        # Merge odds
        print("Merging odds into matches...")
        merged, stats = merge_historical_odds(matches_path, odds_clean_path, merged_path, date_window=2)
        print(f"  Total matches: {stats['total_matches']}")
        print(f"  Matched: {stats['matched']}")
        print(f"  Missing odds after merge: {stats['missing_odds_after']}")

        # Verify
        assert stats["matched"] == 3, f"Expected 3 matches, got {stats['matched']}"
        assert stats["missing_odds_after"] == 1, f"Expected 1 unmatched (FC Dallas), got {stats['missing_odds_after']}"
        merged_df = pd.read_csv(merged_path)
        assert merged_df["odds_home"].notna().sum() == 3

    print()
    print("MLS historical odds smoke test passed.")

if __name__ == "__main__":
    main()
