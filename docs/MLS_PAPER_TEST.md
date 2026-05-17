# MLS Away Paper Test

## What This Is

A structured paper-tracking workflow for a single validated MLS signal:
**Away bets with model edge ≥ 0.04**, filtered by control ≥ 7.0 and chaos ≤ 7.0.

This is **paper testing only** — no real money. The signal has shown repeatable
positive ROI across two OOS seasons (2024, 2025) but has not been validated
over enough bets or time periods to make live betting claims.

## Validated Signal (OOS Backtests)

| Season | Filter | Bets | ROI |
|--------|--------|-----:|----:|
| 2024 OOS | Away edge ≥ 0.04 | 26 | +8.85% |
| 2024 OOS | Away edge ≥ 0.05 | 21 | +34.76% |
| 2025 OOS | Away edge ≥ 0.04 | 116 | +9.18% |
| 2025 OOS | Away edge ≥ 0.05 | 104 | +14.88% |

Away edge ≥ 0.06 shows higher ROI but with smaller samples. Use 0.04 as the
default to accumulate enough bets for statistical validity.

## Gates Applied

All of the following must pass for a bet to be included:

| Gate | Value |
|------|-------|
| League | MLS only |
| Pick side | Away only |
| Away edge | ≥ 0.04 |
| Control model score | ≥ 7.0 |
| Chaos score | ≤ 7.0 |
| Odds available | odds_away must be present and > 1.0 |

**Home bets**: never. No validated Home signal exists in MLS OOS data.  
**Draw bets**: never. Draw ROI was −31.64% in 2025 OOS and −11.85% in 2024 OOS.

## Rules

1. **Stake**: flat 1.0 unit per bet, always. No Kelly or variable staking.
2. **Minimum sample**: judge results only after ≥ 100 tracked bets.
3. **Drawdown limit**: if cumulative profit drops below −20 units, stop and review.
4. **No mid-stream changes**: do not change min-edge, min-control, or max-chaos
   thresholds during an active paper-test run. Change only between seasons.
5. **No live betting**: this is diagnostic paper tracking. Do not place real money
   based solely on this filter.

## How to Generate Candidates

### Step 1 — Predict upcoming MLS fixtures

```bash
fpv19 predict-fixtures \
  --history data/processed/mls_matches_clean_with_odds.csv \
  --fixtures data/upcoming_mls_fixtures.csv \
  --model outputs/model_comparison_mls_2025/best_model.joblib \
  --output outputs/mls_predictions.csv \
  --min-edge 0.04 \
  --min-control 7.0 \
  --max-chaos 7.0
```

### Step 2 — Filter for MLS Away candidates

```bash
python scripts/mls_paper_test.py \
  --input outputs/mls_predictions.csv \
  --mode pending \
  --candidates outputs/paper_test/mls_away_candidates.csv \
  --ledger outputs/paper_test/mls_away_ledger.csv
```

### Step 3 — Settle historical bets into ledger (optional)

```bash
python scripts/mls_paper_test.py \
  --input outputs/backtest_mls_2025.csv \
  --mode settled \
  --candidates outputs/paper_test/mls_away_candidates.csv \
  --ledger outputs/paper_test/mls_away_ledger.csv
```

## Output Columns

| Column | Description |
|--------|-------------|
| date | Match date |
| league | Always MLS |
| home_team | Home team name |
| away_team | Away team name (our pick) |
| pick | Always "Away" |
| odds_away | Bookmaker odds for away win |
| model_away_prob | Model probability for away win |
| edge | Model prob minus implied prob (away) |
| control_score | Control model score (0–10) |
| chaos_score | Chaos score (0–10) |
| status | PENDING (upcoming) or SETTLED (historical) |
| stake | Always 1.0 |
| result | Match result: H/D/A (empty for PENDING) |
| profit | Profit in units (empty for PENDING) |

## What Is Still Missing

- **2022 odds**: No OddsPortal data available — 489 matches without odds.
- **xG data**: FBref MLS export does not include xG. The DNB xG gate is
  inactive. Adding xG data would tighten the filter.
- **Third OOS season**: Two seasons (2024, 2025) confirmed. A third independent
  season would increase confidence before any live consideration.
