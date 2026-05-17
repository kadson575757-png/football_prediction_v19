# Data Requirements

This document describes the expected input formats for each data type.

---

## Historical matches (training data)

### Required columns

| Column | Type | Example | Description |
|---|---|---|---|
| `date` | date | 2023-08-20 | Match date |
| `season` | int/str | 2023 | Season start year |
| `league` | str | Premier League | League name |
| `home_team` | str | Arsenal | Home team (normalized) |
| `away_team` | str | Chelsea | Away team (normalized) |
| `score` | str | 2-1 | Final score (home-away) |
| `home_xg` | float | 1.85 | Home expected goals |
| `away_xg` | float | 0.72 | Away expected goals |
| `odds_home` | float | 2.10 | Bookmaker home win odds |
| `odds_draw` | float | 3.40 | Bookmaker draw odds |
| `odds_away` | float | 3.50 | Bookmaker away win odds |
| `venue` | str | Emirates | Ground name (can be empty) |
| `referee` | str | M. Oliver | Referee name (can be empty) |

### Optional advanced columns (improve model quality when present)

`home_xga`, `away_xga`, `home_shots`, `away_shots`,
`home_shots_on_target`, `away_shots_on_target`,
`home_big_chances`, `away_big_chances`,
`home_possession`, `away_possession`,
`home_ppda`, `away_ppda`,
`home_rest_days`, `away_rest_days`,
`home_injuries_count`, `away_injuries_count`,
`home_market_value`, `away_market_value`

If any of these are missing the project runs normally using the base columns.

---

## Fixture data (upcoming matches)

### Required columns

| Column | Description |
|---|---|
| `date` | Match date |
| `home_team` | Home team name |
| `away_team` | Away team name |

### Optional columns

`season`, `league`, `venue`, `referee`,
`odds_home`, `odds_draw`, `odds_away`,
`formation_home_xg90`, `formation_away_xg90`,
`fatigue_home`, `fatigue_away`

---

## Odds data

### Native format

```
date,home_team,away_team,odds_home,odds_draw,odds_away[,bookmaker,market]
2024-08-17,Arsenal,Chelsea,2.10,3.40,3.50,Bet365,1X2
```

### Supported column aliases (auto-detected)

| Canonical | Accepted aliases |
|---|---|
| `home_team` | `HomeTeam`, `Home` |
| `away_team` | `AwayTeam`, `Away` |
| `odds_home` | `B365H`, `PSH`, `MaxH`, `AvgH` |
| `odds_draw` | `B365D`, `PSD`, `MaxD`, `AvgD` |
| `odds_away` | `B365A`, `PSA`, `MaxA`, `AvgA` |
| `date` | `Date` |

---

## xG data

### Native format

```
date,home_team,away_team,home_xg,away_xg[,source,league,season]
2024-08-17,Arsenal,Chelsea,1.85,0.72,fbref
```

### FBref-style format

```
Date,Home,Away,xG,xG.1[,Comp,Season]
17/08/2024,Arsenal,Chelsea,1.85,0.72,Premier League,2024-2025
```

Column mapping: `xG` → `home_xg`, `xG.1` → `away_xg`, `Comp` → `league`, `Season` → `season`

### Understat-style format

```
date,h_team,a_team,xG,xGA
2024-08-17,Arsenal,Chelsea,1.85,0.72
```

Column mapping: `h_team` → `home_team`, `a_team` → `away_team`,
`xG` → `home_xg`, `xGA` → `away_xg`

Also supported: `home_xG` / `away_xG`

---

## football-data.co.uk format

```
Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A[,PSH,PSD,PSA,MaxH,...]
```

Use `import-football-data` or `--format football-data` with `prepare-data`.
The score is derived from `FTHG` (full-time home goals) and `FTAG`.

---

## FBref-style format

```
Date,Season,Comp,Home,Away,Score,xG,xG.1,Venue,Referee
```

Use `import-fbref` or `--format fbref` with `prepare-data`.

---

## Team name normalization and aliases

Team names are normalized automatically at import time using the alias table in:

```
config/team_aliases.json
```

Example entry:

```json
{
  "Manchester United": ["Man Utd", "Man United", "Manchester Utd"],
  "Tottenham": ["Spurs", "Tottenham Hotspur"]
}
```

Any name in the alias list maps to the canonical name (the key).
Add entries here to handle league-specific or source-specific name variants.
Matching is case-insensitive and strips whitespace.

---

## MLS Support

MLS is supported as a first-class league across the entire pipeline.

### Key differences from Top-5 European leagues

- **FBref CSV importer**: Use `import-mls-fbref` to import FBref-style MLS CSV exports.
- **Odds source**: Use `download-mls-odds` to fetch upcoming odds from The Odds API (sport key: `soccer_usa_mls`). Requires a free API key from https://the-odds-api.com — set `THE_ODDS_API_KEY` environment variable.
- **Not yet validated**: MLS strategies have not been backtested out-of-sample. Do not mix MLS signals with validated Top-5 strategies.

### Historical source: FBref-style CSV

Export MLS match data from FBref and import with:

```
fpv19 import-mls-fbref \
  --input data/raw/mls_fbref_raw.csv \
  --output data/raw/mls_matches.csv
```

Use the template at `data/raw/mls_fbref_raw_template.csv` as a column reference (columns: Date, Home, Away, Score, xG, xG.1, Venue, Referee, Comp, Season).

### Odds source: The Odds API

```
export THE_ODDS_API_KEY=your_key_here
fpv19 download-mls-odds \
  --output data/raw/mls_odds.csv
```

Sport key: `soccer_usa_mls`. Use `--bookmaker` to prefer a specific bookmaker (e.g. `bet365`).

### MLS validation workflow

**A. Prepare data:**
```
fpv19 prepare-mls-data \
  --fbref data/raw/mls_fbref_raw.csv \
  --matches-output data/raw/mls_matches.csv \
  --processed-output data/processed/mls_matches_clean.csv
```

**B. Compare models:**
```
fpv19 compare-models \
  --input data/processed/mls_matches_clean.csv \
  --output-dir outputs/model_comparison_mls \
  --test-season 2024
```

**C. Backtest (strict OOS):**
```
fpv19 backtest-bets \
  --history data/processed/mls_matches_clean.csv \
  --model outputs/model_comparison_mls/best_model.joblib \
  --output outputs/backtest_mls.csv \
  --report outputs/backtest_mls_report.md \
  --test-season 2024 \
  --min-edge 0.03 \
  --max-chaos 7.0 \
  --min-control 7.0
```

**D. Strategy sweep:**
```
python scripts/run_mls_strategy_sweep.py
```

Only after completing steps A-D and reviewing the results should you decide whether MLS strategies are paper-test eligible.

### MLS historical odds

To make MLS backtesting value-capable, you need historical 1X2 odds for your MLS matches.

**Step 1: Obtain historical MLS odds**

Sources that provide historical MLS 1X2 odds (closing or opening):
- OddsPortal (manual export per season)
- The Odds API (historical endpoint, paid tier)
- API-Football (historical odds, paid tier)
- Other bookmaker data providers

Save the file as: `data/raw/mls_historical_odds_raw.csv`

Use the template at `data/raw/mls_historical_odds_template.csv` for the expected column format. The importer accepts many common column name variants automatically.

**Step 2: Import and normalize**

```
fpv19 import-historical-odds \
  --input data/raw/mls_historical_odds_raw.csv \
  --output data/processed/mls_historical_odds_clean.csv \
  --league MLS
```

**Step 3: Merge into MLS match history**

```
fpv19 merge-historical-odds \
  --matches data/raw/mls_matches.csv \
  --odds data/processed/mls_historical_odds_clean.csv \
  --output data/raw/mls_matches_with_odds.csv \
  --date-window 2
```

**Step 4: Re-run validation with odds**

```
fpv19 prepare-mls-data \
  --fbref data/raw/mls_fbref_raw.csv \
  --matches-output data/raw/mls_matches_with_odds.csv \
  --processed-output data/processed/mls_matches_clean.csv

fpv19 compare-models \
  --input data/processed/mls_matches_clean.csv \
  --output-dir outputs/model_comparison_mls \
  --test-season 2025

fpv19 backtest-bets \
  --history data/processed/mls_matches_clean.csv \
  --model outputs/model_comparison_mls/best_model.joblib \
  --output outputs/backtest_mls.csv \
  --report outputs/backtest_mls_report.md \
  --test-season 2025 \
  --min-edge 0.03
```

Only after seeing value bets fire in the backtest should you consider MLS paper-test eligible.

---

## 2. Bundesliga Support

The 2. Bundesliga (Germany's second division) is supported as a first-class league using football-data.co.uk as the data source.

**League codes:**
- Raw div code: `D2`
- Friendly slugs: `bundesliga-2` or `2-bundesliga`
- Human-readable name in processed output: `2. Bundesliga`

**Validation workflow:**

```bash
# Step 1: Download and prepare historical data
fpv19 download-prepare-football-data \
  --leagues D2 \
  --seasons 2021 2022 2023 \
  --raw-dir data/raw \
  --processed-dir data/processed \
  --combine-output data/processed/d2_history_clean.csv

# Step 2: Train a model
fpv19 train \
  --input data/processed/d2_history_clean.csv \
  --model models/d2_model.joblib \
  --test-season 2023

# Step 3: Prepare upcoming fixtures (football-data.co.uk format)
fpv19 prepare-fixtures \
  --input data/raw/d2_upcoming_raw.csv \
  --output data/d2_upcoming.csv \
  --format football-data

# Step 4: Predict
fpv19 predict-fixtures \
  --fixtures data/d2_upcoming.csv \
  --history data/processed/d2_history_clean.csv \
  --model models/d2_model.joblib \
  --output outputs/d2_predictions.csv
```

Use `data/raw/d2_matches_template.csv` as a column reference for the football-data.co.uk format (columns: Div, Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, B365H, B365D, B365A).

Team aliases are automatically normalized (e.g. "HSV" -> "Hamburger SV", "Schalke" -> "FC Schalke 04", "Nurnberg" -> "1. FC Nürnberg").

---

## Eredivisie Support

The Dutch Eredivisie is supported as a first-class league using football-data.co.uk as the data source.

**League codes:**
- Raw div code: `N1`
- Friendly slug: `eredivisie`
- Human-readable name in processed output: `Eredivisie`

**Validation workflow:**

```bash
# Step 1: Download and prepare historical data
fpv19 download-prepare-football-data \
  --leagues N1 \
  --seasons 2021 2022 2023 \
  --raw-dir data/raw \
  --processed-dir data/processed \
  --combine-output data/processed/eredivisie_history_clean.csv

# Step 2: Train a model
fpv19 train \
  --input data/processed/eredivisie_history_clean.csv \
  --model models/eredivisie_model.joblib \
  --test-season 2023

# Step 3: Prepare upcoming fixtures (football-data.co.uk format)
fpv19 prepare-fixtures \
  --input data/raw/eredivisie_upcoming_raw.csv \
  --output data/eredivisie_upcoming.csv \
  --format football-data

# Step 4: Predict
fpv19 predict-fixtures \
  --fixtures data/eredivisie_upcoming.csv \
  --history data/processed/eredivisie_history_clean.csv \
  --model models/eredivisie_model.joblib \
  --output outputs/eredivisie_predictions.csv
```

Use `data/raw/eredivisie_matches_template.csv` as a column reference for the football-data.co.uk format.

Team aliases are automatically normalized (e.g. "Ajax" -> "AFC Ajax", "PSV" -> "PSV Eindhoven", "AZ" -> "AZ Alkmaar", "NEC" -> "NEC Nijmegen").
