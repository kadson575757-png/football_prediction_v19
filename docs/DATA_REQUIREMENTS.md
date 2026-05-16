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

- **No automatic downloader**: MLS data is not available via the `download-prepare-football-data` command. You must provide historical match data manually.
- **Not yet validated**: MLS strategies have not been backtested out-of-sample. Do not mix MLS signals with validated Top-5 strategies.

### Required data file

Provide your MLS historical data as:

```
data/raw/mls_matches.csv
```

Use the template at `data/raw/mls_matches_template.csv` as a column reference.

### MLS validation workflow

**A. Prepare data:**
```
fpv19 prepare-data \
  --input data/raw/mls_matches.csv \
  --output data/processed/mls_matches_clean.csv \
  --format native
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
