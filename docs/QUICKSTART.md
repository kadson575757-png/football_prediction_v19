# Quickstart Guide

This guide gets you from a fresh install to your first football match predictions
in a few minutes using the included sample data.

---

## 1. Install

```bash
cd football_prediction_v19

python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

---

## 2. Check your environment

```bash
fpv19 doctor
```

This verifies Python version, required packages, and project folders.

---

## 3. Run the test suite

```bash
python -m pytest
```

All tests use local sample data — no internet required.

---

## 4. Run a sample pipeline (no internet required)

```bash
fpv19 run-pipeline \
  --skip-download \
  --combine-output data/sample_matches.csv \
  --fixtures-raw data/raw/upcoming_fixtures_raw_template.csv \
  --fixtures-output data/upcoming_fixtures.csv \
  --model models/sample_model.joblib \
  --predictions outputs/predictions.csv \
  --excel outputs/predictions_report.xlsx \
  --test-season 2023
```

Outputs land in `outputs/` and `models/`.

---

## 5. Prepare real football-data.co.uk data

Download and prepare historical data for one or more leagues:

```bash
fpv19 download-prepare-football-data \
  --leagues E0 D1 \
  --seasons 2022 2023 \
  --raw-dir data/raw \
  --processed-dir data/processed \
  --combine-output data/processed/combined_football_data.csv
```

Or import an existing CSV:

```bash
fpv19 import-football-data \
  --input data/raw/football_data.csv \
  --output data/processed/football_data_clean.csv
```

---

## 6. Prepare upcoming fixtures

```bash
fpv19 prepare-fixtures \
  --input data/raw/upcoming_fixtures_raw.csv \
  --output data/upcoming_fixtures.csv \
  --format auto
```

---

## 7. Add bookmaker odds (optional)

```bash
fpv19 prepare-odds \
  --input data/raw/odds_raw.csv \
  --output data/processed/odds_clean.csv

fpv19 merge-odds-fixtures \
  --fixtures data/upcoming_fixtures.csv \
  --odds data/processed/odds_clean.csv \
  --output data/upcoming_fixtures_with_odds.csv
```

---

## 8. Add xG data (optional)

```bash
fpv19 prepare-xg \
  --input data/raw/xg_raw.csv \
  --output data/processed/xg_clean.csv \
  --format auto

fpv19 merge-xg-history \
  --history data/processed/combined_football_data.csv \
  --xg data/processed/xg_clean.csv \
  --output data/processed/combined_football_data_with_xg.csv
```

---

## 9. Train and compare models

Single model:

```bash
fpv19 train \
  --input data/processed/combined_football_data.csv \
  --model models/model.joblib \
  --test-season 2023
```

Compare all model families and pick the best:

```bash
fpv19 compare-models \
  --input data/processed/combined_football_data.csv \
  --output-dir outputs/model_comparison \
  --test-season 2023
```

---

## 10. Predict upcoming fixtures

```bash
fpv19 predict-fixtures \
  --history data/processed/combined_football_data.csv \
  --fixtures data/upcoming_fixtures.csv \
  --model models/model.joblib \
  --output outputs/predictions.csv
```

---

## 11. Export Excel dashboard

Basic (predictions only):

```bash
fpv19 export-excel \
  --predictions outputs/predictions.csv \
  --output outputs/predictions_report.xlsx
```

Full dashboard with model comparison and backtest:

```bash
fpv19 export-excel \
  --predictions outputs/predictions.csv \
  --output outputs/predictions_report.xlsx \
  --model-comparison outputs/model_comparison/model_comparison.csv \
  --model-metadata outputs/model_comparison/best_model_metadata.json \
  --backtest-csv outputs/backtest_bets.csv
```

---

## Output file locations

| File | Description |
|---|---|
| `outputs/predictions.csv` | Fixture-level predictions |
| `outputs/predictions_report.xlsx` | Excel dashboard |
| `outputs/backtest_bets.csv` | Backtest bet-by-bet results |
| `outputs/model_comparison/` | Model comparison CSV, report, best model |
| `models/` | Trained model files (.joblib) |
| `data/processed/` | Cleaned and combined historical data |
