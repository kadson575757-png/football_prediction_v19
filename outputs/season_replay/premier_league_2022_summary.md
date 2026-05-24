# Season Replay Audit — Premier League 2022

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 87
- Predictions with OK model : 276
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 276
- Evaluatable (type): 227
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     30    18   60.0%  
  BTTS_OVER                 74    48   64.9%  over25=42/74  btts=40/74
  DIRECTION                 11     7   63.6%    ⚠ n<20
  DOUBLE_CHANCE            103    82   79.6%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      9     5   55.6%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            37    17   45.9%  BTTS_OVER
  BTTS                        25    16   64.0%  BTTS_OVER
  DIRECTION_AWAY               3     1   33.3%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               6     5   83.3%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            61    49   80.3%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            42    33   78.6%  DOUBLE_CHANCE
  OVER_25                     12     3   25.0%  BTTS_OVER  ⚠ n<20
  UNDER_35                     9     5   55.6%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 48/74  (64.9%)
  Subtype BOTH_OVER25_BTTS      : 17/37  (45.9%)
  Subtype BTTS                  : 16/25  (64.0%)
  Subtype OVER_25               : 3/12  (25.0%)

### Best Performing Subtypes
  DIRECTION_HOME           83.3%  (5/6)
  DOUBLE_CHANCE_1X         80.3%  (49/61)
  DOUBLE_CHANCE_X2         78.6%  (33/42)
  BTTS                     64.0%  (16/25)
  UNDER_35                 55.6%  (5/9)

### Worst Performing Subtypes
  OVER_25                  25.0%  (3/12)
  DIRECTION_AWAY           33.3%  (1/3)
  BOTH_OVER25_BTTS         45.9%  (17/37)
  UNDER_35                 55.6%  (5/9)
  BTTS                     64.0%  (16/25)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             33    23   69.7%
  low (3-5)               84    54   64.3%
  medium (5-7)           110    83   75.5%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              1     1  100.0%  ⚠ small sample
  low (<4)               142   105   73.9%
  medium (4-6)            84    54   64.3%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                28    19   67.9%
  LOW                 43    32   74.4%
  MEDIUM             155   108   69.7%
  NO-CONFIDENCE        1     1  100.0%  ⚠ small sample

## Success by Season Phase

  early           16    10   62.5%  ⚠ small sample
  mid            100    64   64.0%
  late           111    86   77.5%

## Success by Odds Bucket

  heavy_fav (<=1.5)               52    36   69.2%
  medium_fav (2.0-2.5)            65    38   58.5%
  no_clear_fav (>2.5)             21    16   76.2%
  strong_fav (1.5-2.0)            89    70   78.7%

## AVOID Diagnostic

  Total AVOID calls  : 30
  Correctly avoided  : 18 / 30  (60.0%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 4/9
  Under 3.5 hit  : 5/9
  Type OR success: 5/9  (55.6%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Fulham v Aston Villa                 AVOID            AVOID_VOLATILE         H        3g
  Leicester v Leeds                    BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Wolves v Leicester                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        4g
  Fulham v Everton                     BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Crystal Palace v Southampton         BTTS_OVER        BTTS                   H        1g
  Leicester v Man City                 BTTS_OVER        OVER_25                A        1g
  Everton v Leicester                  AVOID            AVOID_VOLATILE         A        2g
  West Ham v Crystal Palace            DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Chelsea v Arsenal                    BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Aston Villa v Man United             DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        4g
  Newcastle v Chelsea                  BTTS_OVER        BTTS                   H        1g
  West Ham v Leicester                 AVOID            AVOID_VOLATILE         A        2g
  Bournemouth v Everton                AVOID            AVOID_VOLATILE         H        3g
  Arsenal v West Ham                   DIRECTION        DIRECTION_AWAY         H        4g
  Crystal Palace v Fulham              AVOID            AVOID_VOLATILE         A        3g
  Everton v Wolves                     AVOID            AVOID_VOLATILE         A        3g
  West Ham v Brentford                 AVOID            AVOID_VOLATILE         A        2g
  Newcastle v Leeds                    BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Tottenham v Aston Villa              BTTS_OVER        OVER_25                A        2g
  Leicester v Fulham                   BTTS_OVER        OVER_25                A        1g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Chelsea v Man United                 AVOID            AVOID_VOLATILE         D        2g
  Everton v Crystal Palace             BTTS_OVER        BTTS                   H        3g
  Aston Villa v Brentford              DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Leeds v Fulham                       BTTS_OVER        BOTH_OVER25_BTTS       A        5g
  Southampton v Arsenal                BTTS_OVER        OVER_25                D        2g
  West Ham v Bournemouth               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Brentford v Wolves                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Bournemouth v Tottenham              DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        5g
  Arsenal v Nott'm Forest              BTTS_OVER        OVER_25                H        5g
  Man United v West Ham                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Leeds v Bournemouth                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        7g
  Man City v Fulham                    BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Nott'm Forest v Brentford            DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        4g
  Wolves v Brighton                    DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        5g
  Southampton v Newcastle              DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        5g
  Tottenham v Leeds                    BTTS_OVER        BTTS                   H        7g
  Fulham v Man United                  BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Brentford v Tottenham                BTTS_OVER        BOTH_OVER25_BTTS       D        4g
  Leicester v Newcastle                DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  Southampton v Brighton               BTTS_OVER        BTTS                   A        4g

## Sample Size Warnings

  ⚠ DIRECTION: only 11 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 9 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 3 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 6 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype UNDER_35: only 9 evaluatable matches.

---
## Leakage-Safety Confirmation

| Check | Status |
|---|---|
| train_df excludes current matchday | ✅ prior_df/prior_ml filtered by date < cutoff_date |
| train_df excludes future matchdays | ✅ strict < not <= cutoff |
| Current match result not used as feature | ✅ build_fixture_features uses history_df[date < match_date] |
| No full-season pre-trained model | ✅ model fitted fresh per cutoff (or once at first eligible) |
| Cross-match contamination on same date | ✅ all matches in a group share the same prior_df snapshot |

---
*This report is diagnostic only. No betting, staking, or ROI claims.*