# CLI Command Reference

All commands use the `fpv19` entry point. Run `fpv19 <command> --help` for full usage.

---

## doctor

Check environment health: Python version, required packages, and project folders.

```bash
fpv19 doctor
```

No required inputs. Exits non-zero only if something critical is missing.

---

## train

Train a model on historical match data.

```bash
fpv19 train \
  --input data/processed/combined_football_data.csv \
  --model models/model.joblib \
  --test-season 2023
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Path to processed historical matches CSV |
| `--model` | yes | Where to save the trained model (.joblib) |
| `--test-season` | no | Season year to hold out for evaluation |
| `--model-type` | no | `random_forest` (default), `logistic_regression`, `gradient_boosting` |
| `--tune` | no | Enable hyperparameter tuning (slower) |

---

## predict

Predict a single match.

```bash
fpv19 predict \
  --history data/processed/combined_football_data.csv \
  --model models/model.joblib \
  --home Arsenal \
  --away Chelsea \
  --date 2024-05-01
```

| Flag | Required | Description |
|---|---|---|
| `--history` | yes | Historical matches CSV for feature context |
| `--model` | yes | Trained model (.joblib) |
| `--home` | yes | Home team name |
| `--away` | yes | Away team name |
| `--date` | no | Match date (YYYY-MM-DD) |
| `--odds-home/draw/away` | no | Bookmaker odds for value edge calculation |

---

## predict-fixtures

Predict a list of upcoming fixtures.

```bash
fpv19 predict-fixtures \
  --history data/processed/combined_football_data.csv \
  --fixtures data/upcoming_fixtures.csv \
  --model models/model.joblib \
  --output outputs/predictions.csv
```

| Flag | Required | Description |
|---|---|---|
| `--history` | yes | Historical matches CSV |
| `--fixtures` | yes | Prepared upcoming fixtures CSV |
| `--model` | yes | Trained model (.joblib) |
| `--output` | yes | Where to save predictions CSV |
| `--min-edge` | no | Minimum edge for bet recommendation (default 0.03) |

---

## prepare-data

Prepare a raw historical matches CSV into a clean training-ready format.

Supported leagues include Premier League, Championship, Bundesliga, Bundesliga 2, Serie A, Serie B,
La Liga, Segunda Division, Ligue 1, Ligue 2, Eredivisie, Pro League, Primeira Liga, Super Lig,
Super League Greece, Scottish Premiership, and **MLS** (native format only — no automatic downloader).

```bash
fpv19 prepare-data \
  --input data/raw/real_matches.csv \
  --output data/processed/real_matches_clean.csv \
  --format auto
```

MLS example (native format):

```bash
fpv19 prepare-data \
  --input data/raw/mls_matches.csv \
  --output data/processed/mls_matches_clean.csv \
  --format native
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Raw matches CSV |
| `--output` | yes | Output cleaned CSV |
| `--format` | no | `auto` (default), `native`, `fbref`, `football-data` |

---

## import-football-data

Import a football-data.co.uk style CSV.

```bash
fpv19 import-football-data \
  --input data/raw/football_data.csv \
  --output data/processed/football_data_clean.csv
```

---

## import-fbref

Import an FBref-style CSV.

```bash
fpv19 import-fbref \
  --input data/raw/fbref_matches.csv \
  --output data/processed/fbref_matches_clean.csv
```

---

## import-and-prepare

Auto-detect format and import + prepare in one step.

```bash
fpv19 import-and-prepare \
  --input data/raw/real_matches.csv \
  --output data/processed/real_matches_clean.csv \
  --format auto
```

---

## download-football-data

Download raw football-data.co.uk CSV for a single league and season.

```bash
fpv19 download-football-data \
  --league E0 \
  --season 2023 \
  --output data/raw/football_data_E0_2023.csv
```

---

## download-prepare-football-data

Download and prepare multiple leagues and seasons in one step.

```bash
fpv19 download-prepare-football-data \
  --leagues E0 D1 I1 \
  --seasons 2022 2023 \
  --raw-dir data/raw \
  --processed-dir data/processed \
  --combine-output data/processed/combined_football_data.csv
```

| Flag | Required | Description |
|---|---|---|
| `--leagues` | yes | One or more league codes (e.g. E0 D1 I1) |
| `--seasons` | yes | One or more season start years (e.g. 2022 2023) |
| `--raw-dir` | yes | Where raw CSVs are saved |
| `--processed-dir` | yes | Where cleaned CSVs are saved |
| `--combine-output` | no | Optional combined output CSV |

---

## prepare-fixtures

Convert a raw upcoming fixtures CSV to prediction-ready format.

```bash
fpv19 prepare-fixtures \
  --input data/raw/upcoming_fixtures_raw.csv \
  --output data/upcoming_fixtures.csv \
  --format auto
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Raw fixtures CSV |
| `--output` | yes | Prepared fixtures CSV |
| `--format` | no | `auto` (default), `native`, `football-data` |
| `--default-season` | no | Default season if not in file |
| `--default-league` | no | Default league if not in file |

---

## prepare-odds

Prepare a raw odds CSV (supports native, B365H/PSH/MaxH aliases).

```bash
fpv19 prepare-odds \
  --input data/raw/odds_raw.csv \
  --output data/processed/odds_clean.csv
```

---

## merge-odds-fixtures

Merge odds into a prepared fixtures file by team name and date.

```bash
fpv19 merge-odds-fixtures \
  --fixtures data/upcoming_fixtures.csv \
  --odds data/processed/odds_clean.csv \
  --output data/upcoming_fixtures_with_odds.csv \
  --allow-date-window 1
```

| Flag | Required | Description |
|---|---|---|
| `--fixtures` | yes | Prepared fixtures CSV |
| `--odds` | yes | Cleaned odds CSV |
| `--output` | yes | Output CSV with odds merged in |
| `--allow-date-window` | no | Match within ±N days (default 0 = exact) |
| `--prefer` | no | Prefer rows from this bookmaker name |

---

## prepare-xg

Prepare a raw xG CSV (supports native, FBref, Understat formats).

```bash
fpv19 prepare-xg \
  --input data/raw/xg_raw.csv \
  --output data/processed/xg_clean.csv \
  --format auto
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Raw xG CSV |
| `--output` | yes | Cleaned xG CSV |
| `--format` | no | `auto` (default), `native`, `fbref`, `understat` |

---

## merge-xg-history

Merge xG values into historical match data. Also derives home_xga / away_xga.

```bash
fpv19 merge-xg-history \
  --history data/processed/combined_football_data.csv \
  --xg data/processed/xg_clean.csv \
  --output data/processed/combined_football_data_with_xg.csv \
  --allow-date-window 1
```

| Flag | Required | Description |
|---|---|---|
| `--history` | yes | Historical matches CSV |
| `--xg` | yes | Cleaned xG CSV |
| `--output` | yes | Output enriched history CSV |
| `--allow-date-window` | no | Match within ±N days (default 0 = exact) |
| `--prefer-source` | no | Prefer rows where source equals this value |

---

## backtest-bets

Run a betting simulation on historical data.

```bash
fpv19 backtest-bets \
  --history data/processed/combined_football_data.csv \
  --model models/model.joblib \
  --output outputs/backtest_bets.csv \
  --report outputs/backtest_report.md \
  --test-season 2023
```

---

## compare-models

Train and compare Logistic Regression, Random Forest, and Gradient Boosting.
Saves the best model (by log loss, then Brier score).

```bash
fpv19 compare-models \
  --input data/processed/combined_football_data.csv \
  --output-dir outputs/model_comparison \
  --test-season 2023
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Historical matches CSV |
| `--output-dir` | yes | Directory for all outputs |
| `--test-season` | yes | Season year to hold out for evaluation |
| `--target` | no | Target column (default: result) |
| `--random-state` | no | Random seed (default: 42) |

Outputs: `model_comparison.csv`, `model_comparison_report.md`,
`best_model.joblib`, `feature_columns.json`, `best_model_metadata.json`.

---

## export-excel

Create an Excel workbook from prediction results. Optional dashboard sheets
are added when comparison/backtest files are provided.

```bash
fpv19 export-excel \
  --predictions outputs/predictions.csv \
  --output outputs/predictions_report.xlsx \
  --model-comparison outputs/model_comparison/model_comparison.csv \
  --model-metadata outputs/model_comparison/best_model_metadata.json \
  --backtest-csv outputs/backtest_bets.csv
```

| Flag | Required | Description |
|---|---|---|
| `--predictions` | yes | Predictions CSV |
| `--output` | yes | Output .xlsx path |
| `--model-comparison` | no | model_comparison.csv for dashboard sheets |
| `--model-metadata` | no | best_model_metadata.json for Best Model sheet |
| `--backtest-csv` | no | backtest_bets.csv for Backtest sheets |

---

## run-pipeline

End-to-end workflow: download → prepare → xG/odds enrich → train/compare → predict → Excel → backtest.

```bash
fpv19 run-pipeline \
  --skip-download \
  --combine-output data/processed/combined_football_data.csv \
  --fixtures-raw data/raw/upcoming_fixtures_raw.csv \
  --fixtures-output data/upcoming_fixtures.csv \
  --model models/model.joblib \
  --predictions outputs/predictions.csv \
  --excel outputs/predictions_report.xlsx \
  --test-season 2023
```

Key optional flags:

| Flag | Description |
|---|---|
| `--skip-download` | Skip download; use existing --combine-output |
| `--use-existing-fixtures` | Skip prepare-fixtures; use existing --fixtures-output |
| `--skip-backtest` | Skip the backtest step |
| `--compare-models` | Use compare-models instead of single train |
| `--compare-models-dir` | Where compare-models outputs are saved |
| `--odds-raw` | Raw odds CSV; triggers prepare-odds + merge |
| `--xg-raw` | Raw xG CSV; triggers prepare-xg + merge into history |
| `--test-season` | Season year to hold out for evaluation / backtest |

---

## import-mls-fbref

Import a FBref-style MLS CSV export and normalize it to the project schema.

```bash
fpv19 import-mls-fbref \
  --input data/raw/mls_fbref_raw.csv \
  --output data/raw/mls_matches.csv
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Path to FBref-style MLS CSV (columns: Date, Home, Away, Score, xG, xG.1, Venue, Referee, Comp, Season) |
| `--output` | yes | Path where the normalized matches CSV is saved |

Use `data/raw/mls_fbref_raw_template.csv` as a column reference template.

---

## download-mls-odds

Fetch upcoming MLS odds from The Odds API (sport key: `soccer_usa_mls`).
Requires a free API key from https://the-odds-api.com.

```bash
export THE_ODDS_API_KEY=your_key_here
fpv19 download-mls-odds \
  --output data/raw/mls_odds.csv
```

| Flag | Required | Description |
|---|---|---|
| `--output` | yes | Path where the odds CSV is saved |
| `--api-key` | no | API key (overrides THE_ODDS_API_KEY env var) |
| `--regions` | no | Regions for odds, e.g. `us` (default: us) |
| `--markets` | no | Markets to fetch, e.g. `h2h` (default: h2h) |
| `--odds-format` | no | `decimal` or `american` (default: decimal) |
| `--bookmaker` | no | Preferred bookmaker key, e.g. `bet365` |

---

## prepare-mls-data

Import a FBref-style MLS CSV and prepare it for model training in one step.

```bash
fpv19 prepare-mls-data \
  --fbref data/raw/mls_fbref_raw.csv \
  --matches-output data/raw/mls_matches.csv \
  --processed-output data/processed/mls_matches_clean.csv
```

| Flag | Required | Description |
|---|---|---|
| `--fbref` | yes | Path to FBref-style MLS CSV export |
| `--matches-output` | yes | Path where the normalized matches CSV is saved |
| `--processed-output` | yes | Path where the cleaned/processed CSV is saved |

## import-historical-odds

Import historical odds from any CSV with flexible column names and normalize to project schema.

```bash
fpv19 import-historical-odds \
  --input data/raw/mls_historical_odds_raw.csv \
  --output data/processed/mls_historical_odds_clean.csv \
  --league MLS
```

| Flag | Required | Description |
|---|---|---|
| `--input` | yes | Input odds CSV file (accepts many column name variants) |
| `--output` | yes | Output normalized odds CSV |
| `--league` | no | League name (default: MLS) |

The importer automatically maps common column aliases for date, home/away team, and 1X2 odds. Use `data/raw/mls_historical_odds_template.csv` as a column reference.

## merge-historical-odds

Merge historical odds into a matches CSV by date and team name matching.

```bash
fpv19 merge-historical-odds \
  --matches data/raw/mls_matches.csv \
  --odds data/processed/mls_historical_odds_clean.csv \
  --output data/raw/mls_matches_with_odds.csv \
  --date-window 2
```

| Flag | Required | Description |
|---|---|---|
| `--matches` | yes | Matches CSV file to enrich with odds |
| `--odds` | yes | Normalized odds CSV (output of `import-historical-odds`) |
| `--output` | yes | Output matches CSV with odds_home/draw/away filled in |
| `--date-window` | no | Tolerance in days for date matching (default: 2) |
| `--overwrite` | no | Overwrite existing non-null odds (default: skip) |
