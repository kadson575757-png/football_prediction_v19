"""MLS data sources smoke test. Requires no internet. Uses local template files."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
from pathlib import Path
from football_prediction_v19.importers.mls_fbref import import_mls_fbref
from football_prediction_v19.importers.the_odds_api import parse_the_odds_api_events
from football_prediction_v19.data import prepare_real_matches
import pandas as pd

BASE = Path(__file__).parent.parent

def main():
    # 1. Import FBref template
    fbref_path = BASE / "data/raw/mls_fbref_raw_template.csv"
    matches_path = BASE / "data/raw/mls_matches_from_template.csv"
    print(f"Importing FBref template: {fbref_path}")
    df = import_mls_fbref(fbref_path, matches_path)
    print(f"  Imported {len(df)} rows -> {matches_path}")

    # 2. Prepare data
    processed_path = BASE / "data/processed/mls_matches_from_template_clean.csv"
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    clean = prepare_real_matches(df)
    clean.to_csv(processed_path, index=False)
    print(f"  Prepared {len(clean)} rows -> {processed_path}")

    # 3. Parse odds sample
    sample_path = BASE / "data/raw/mls_the_odds_api_sample.json"
    odds_path = BASE / "data/raw/mls_odds_from_sample.csv"
    print(f"Parsing odds sample: {sample_path}")
    with open(sample_path) as f:
        payload = json.load(f)
    odds = parse_the_odds_api_events(payload)
    odds.to_csv(odds_path, index=False)
    print(f"  Parsed {len(odds)} odds rows -> {odds_path}")

    print()
    print("NOTE: This uses template/sample data only. Not claiming predictive quality.")
    print("MLS sources smoke test passed.")

if __name__ == "__main__":
    main()
