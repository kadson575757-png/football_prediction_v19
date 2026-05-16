"""MLS smoke test: verifies MLS data flows through the pipeline without errors.
Does NOT claim predictive quality. Requires no internet.
"""
from __future__ import annotations
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from football_prediction_v19.features import build_features, build_fixture_features


def make_mls_sample() -> pd.DataFrame:
    rows = []
    teams = [
        ("LA Galaxy", "Inter Miami"),
        ("Seattle Sounders", "Portland Timbers"),
        ("Atlanta United", "Orlando City"),
        ("New York City FC", "New York Red Bulls"),
        ("Sporting Kansas City", "Columbus Crew"),
    ]
    import random
    random.seed(42)
    for season in [2023, 2024]:
        for home, away in teams:
            for _ in range(3):
                hg = random.randint(0, 3)
                ag = random.randint(0, 3)
                rows.append({
                    "date": f"{season}-05-{random.randint(1, 28):02d}",
                    "season": str(season),
                    "league": "MLS",
                    "home_team": home,
                    "away_team": away,
                    "score": f"{hg}-{ag}",
                    "home_xg": round(random.uniform(0.5, 2.5), 2),
                    "away_xg": round(random.uniform(0.5, 2.5), 2),
                    "odds_home": round(random.uniform(1.5, 4.0), 2),
                    "odds_draw": round(random.uniform(2.8, 4.5), 2),
                    "odds_away": round(random.uniform(1.5, 4.0), 2),
                    "venue": "Example Stadium",
                    "referee": "",
                })
    return pd.DataFrame(rows)


def main_smoke():
    print("MLS smoke test: building sample dataset...")
    df = make_mls_sample()
    print(f"  Sample rows: {len(df)}, leagues: {df['league'].unique()}")

    print("MLS smoke test: running build_features...")
    features = build_features(df)
    print(f"  Feature rows: {len(features)}, leagues: {features['league'].unique() if 'league' in features.columns else 'N/A'}")

    print("MLS smoke test: running build_fixture_features...")
    fix = build_fixture_features(
        history_df=df,
        home_team="LA Galaxy",
        away_team="Inter Miami",
        match_date="2025-01-15",
        venue="Dignity Health Sports Park",
    )
    print(f"  Fixture features shape: {fix.shape}")

    print()
    print("NOTE: This smoke test does NOT claim predictive quality.")
    print("MLS strategies must be validated separately before paper testing.")
    print()
    print("MLS smoke test passed.")


if __name__ == "__main__":
    main_smoke()
