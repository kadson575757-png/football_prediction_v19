# -*- coding: utf-8 -*-
"""
Build historical totals odds raw file and combined match file,
then run the full import-merge-audit pipeline.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Step 1: Build combined matches file from all individual clean files
# ---------------------------------------------------------------------------
print("=== Step 1: Build combined matches file ===")
clean_dir = ROOT / "data" / "processed"
frames = []
for f in sorted(clean_dir.glob("football_data_*_clean.csv")):
    df = pd.read_csv(f)
    frames.append(df)

combined = pd.concat(frames, ignore_index=True)
combined["date"] = pd.to_datetime(combined["date"])
combined = combined.sort_values("date").reset_index(drop=True)
combined = combined.drop_duplicates(subset=["date", "home_team", "away_team"])
combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

out_matches = ROOT / "data" / "processed" / "all_leagues_2021_2025_clean.csv"
combined.to_csv(out_matches, index=False)
print(f"  {len(combined)} rows -> {out_matches}")
combined["_yr"] = pd.to_datetime(combined["date"]).dt.year
print(f"  leagues: {sorted(combined['league'].unique())}")
print(f"  years:   {sorted(combined['_yr'].unique().tolist())}")
combined = combined.drop(columns=["_yr"])


# ---------------------------------------------------------------------------
# Step 2: Build historical_totals_odds_raw.csv from all raw files with B365 cols
# ---------------------------------------------------------------------------
print("\n=== Step 2: Extract B365>2.5 / B365<2.5 from raw files ===")
raw_dir = ROOT / "data" / "raw"
over_col = "B365>2.5"
under_col = "B365<2.5"

div_to_league = {
    "D1": "Bundesliga",
    "D2": "2. Bundesliga",
    "E0": "Premier League",
    "F1": "Ligue 1",
    "I1": "Serie A",
    "N1": "Eredivisie",
    "SP1": "La Liga",
}

odds_frames = []
files_found = []
for f in sorted(raw_dir.glob("football_data_*.csv")):
    try:
        df = pd.read_csv(f, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(f, encoding="latin-1")

    if over_col not in df.columns:
        continue

    # Resolve league
    div = df["Div"].iloc[0] if "Div" in df.columns else "??"
    league = div_to_league.get(div, div)

    # Pick needed columns
    out_rows = pd.DataFrame({
        "Date": df.get("Date", pd.Series(dtype=str)),
        "HomeTeam": df.get("HomeTeam", pd.Series(dtype=str)),
        "AwayTeam": df.get("AwayTeam", pd.Series(dtype=str)),
        "B365>2.5": pd.to_numeric(df[over_col], errors="coerce"),
        "B365<2.5": pd.to_numeric(df[under_col], errors="coerce") if under_col in df.columns else np.nan,
        "_league": league,
    })
    out_rows = out_rows.dropna(subset=["B365>2.5"])
    odds_frames.append(out_rows)
    files_found.append((f.name, len(out_rows), league))

for name, n, lg in files_found:
    print(f"  {name}: {n} rows  ({lg})")

all_odds = pd.concat(odds_frames, ignore_index=True)
all_odds = all_odds.drop(columns=["_league"])

out_totals_raw = ROOT / "data" / "raw" / "historical_totals_odds_raw.csv"
all_odds.to_csv(out_totals_raw, index=False)
print(f"\n  Total odds rows: {len(all_odds)} -> {out_totals_raw}")


# ---------------------------------------------------------------------------
# Step 3: fpv19 import-totals-odds
# ---------------------------------------------------------------------------
print("\n=== Step 3: fpv19 import-totals-odds ===")
out_totals_clean = ROOT / "data" / "processed" / "historical_totals_odds_clean.csv"
result = subprocess.run(
    [sys.executable, "-m", "football_prediction_v19.cli",
     "import-totals-odds",
     "--input", str(out_totals_raw),
     "--output", str(out_totals_clean)],
    capture_output=True, text=True, cwd=ROOT
)
print(result.stdout.strip())
if result.returncode != 0:
    print("STDERR:", result.stderr.strip())
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 4: fpv19 merge-totals-odds
# ---------------------------------------------------------------------------
print("\n=== Step 4: fpv19 merge-totals-odds ===")
out_with_totals = ROOT / "data" / "processed" / "matches_clean_with_totals.csv"
result = subprocess.run(
    [sys.executable, "-m", "football_prediction_v19.cli",
     "merge-totals-odds",
     "--matches", str(out_matches),
     "--odds", str(out_totals_clean),
     "--output", str(out_with_totals),
     "--date-window", "2",
     "--overwrite"],
    capture_output=True, text=True, cwd=ROOT
)
print(result.stdout.strip())
if result.returncode != 0:
    print("STDERR:", result.stderr.strip())
    sys.exit(1)

# Coverage check
merged = pd.read_csv(out_with_totals)
total = len(merged)
with_odds = merged["odds_over25"].notna().sum()
print(f"\n  Coverage: {with_odds}/{total} rows have odds_over25 ({with_odds/total*100:.1f}%)")

if "league" in merged.columns:
    print("\n  Per-league coverage:")
    for lg, sub in merged.groupby("league"):
        n_o = sub["odds_over25"].notna().sum()
        print(f"    {lg}: {n_o}/{len(sub)} ({n_o/len(sub)*100:.0f}%)")


# ---------------------------------------------------------------------------
# Step 5: run_form_over25_real_odds_audit.py
# ---------------------------------------------------------------------------
print("\n=== Step 5: run_form_over25_real_odds_audit.py ===")
result = subprocess.run(
    [sys.executable,
     str(ROOT / "scripts" / "run_form_over25_real_odds_audit.py"),
     "--matches", str(out_with_totals)],
    capture_output=True, text=True, cwd=ROOT
)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr.strip())
    sys.exit(1)

print("=== Pipeline complete ===")
