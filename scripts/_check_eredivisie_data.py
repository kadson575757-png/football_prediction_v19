import pandas as pd
import joblib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

files = [
    "data/processed/eredivisie_clean.csv",
    "data/processed/football_data_N1_2021_clean.csv",
    "data/processed/football_data_N1_2022_clean.csv",
    "data/processed/football_data_N1_2023_clean.csv",
    "data/processed/football_data_N1_2024_clean.csv",
    "data/processed/matches_clean_with_totals.csv",
]

for f in files:
    p = ROOT / f
    if p.exists():
        df = pd.read_csv(p, parse_dates=["date"] if "date" in pd.read_csv(p, nrows=0).columns else [])
        ered = df[df.get("league", pd.Series(["?"])).isin(["Eredivisie"])] if "league" in df.columns else df
        print(f"FOUND  {f}")
        print(f"  total={len(df)}  eredivisie={len(ered)}  cols={list(df.columns)[:10]}")
        if "date" in df.columns:
            print(f"  dates: {df.date.min()} to {df.date.max()}")
        if "home_team" in df.columns:
            teams = sorted(set(ered.home_team.unique().tolist()))
            print(f"  teams (sample): {teams[:10]}")
    else:
        print(f"MISSING {f}")
    print()

print("=== Models ===")
for m in ["outputs/model_comparison_eredivisie/best_model.joblib",
          "outputs/model_comparison_top5/best_model.joblib",
          "models/real_model.joblib"]:
    p = ROOT / m
    if p.exists():
        mb = joblib.load(p)
        if isinstance(mb, dict):
            print(f"FOUND {m}")
            print(f"  classes={mb['model'].classes_}")
            print(f"  accuracy={mb['metrics'].get('accuracy', '?'):.3f}")
    else:
        print(f"MISSING {m}")

print()
# Check fixture file
fx = ROOT / "data/upcoming_eredivisie_fixtures.csv"
if fx.exists():
    df = pd.read_csv(fx)
    print(f"Fixture file found: {len(df)} rows")
    print(df.to_string())
else:
    print("Fixture file MISSING - need to create it")
