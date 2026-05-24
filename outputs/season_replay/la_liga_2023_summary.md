# Season Replay Audit — La Liga 2023

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 106
- Predictions with OK model : 280
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 280
- Evaluatable (type): 230
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     20    16   80.0%  
  BTTS_OVER                 70    41   58.6%  over25=33/70  btts=34/70
  DIRECTION                 13     9   69.2%    ⚠ n<20
  DOUBLE_CHANCE            114    95   83.3%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                     13    11   84.6%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            13     5   38.5%  BTTS_OVER  ⚠ n<20
  BTTS                        51    26   51.0%  BTTS_OVER
  DIRECTION_AWAY               3     1   33.3%  DIRECTION  ⚠ n<20
  DIRECTION_HOME              10     8   80.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            76    65   85.5%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            38    30   78.9%  DOUBLE_CHANCE
  OVER_25                      6     1   16.7%  BTTS_OVER  ⚠ n<20
  UNDER_35                    13    11   84.6%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 41/70  (58.6%)
  Subtype BOTH_OVER25_BTTS      : 5/13  (38.5%)
  Subtype BTTS                  : 26/51  (51.0%)
  Subtype OVER_25               : 1/6  (16.7%)

### Best Performing Subtypes
  DOUBLE_CHANCE_1X         85.5%  (65/76)
  UNDER_35                 84.6%  (11/13)
  DIRECTION_HOME           80.0%  (8/10)
  DOUBLE_CHANCE_X2         78.9%  (30/38)
  BTTS                     51.0%  (26/51)

### Worst Performing Subtypes
  OVER_25                  16.7%  (1/6)
  DIRECTION_AWAY           33.3%  (1/3)
  BOTH_OVER25_BTTS         38.5%  (5/13)
  BTTS                     51.0%  (26/51)
  DOUBLE_CHANCE_X2         78.9%  (30/38)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             27    18   66.7%
  low (3-5)               94    67   71.3%
  medium (5-7)           109    87   79.8%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               156   129   82.7%
  medium (4-6)            74    43   58.1%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                27    18   66.7%
  LOW                 58    47   81.0%
  MEDIUM             144   106   73.6%
  NO-CONFIDENCE        1     1  100.0%  ⚠ small sample

## Success by Season Phase

  early           16    11   68.8%  ⚠ small sample
  mid            106    74   69.8%
  late           108    87   80.6%

## Success by Odds Bucket

  heavy_fav (<=1.5)               36    27   75.0%
  medium_fav (2.0-2.5)            82    60   73.2%
  no_clear_fav (>2.5)             19    11   57.9%  ⚠ small sample
  strong_fav (1.5-2.0)            93    74   79.6%

## AVOID Diagnostic

  Total AVOID calls  : 20
  Correctly avoided  : 16 / 20  (80.0%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 9/13
  Under 3.5 hit  : 11/13
  Type OR success: 11/13  (84.6%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Mallorca v Getafe                    BTTS_OVER        BTTS                   D        0g
  Barcelona v Real Madrid              AVOID            AVOID_VOLATILE         A        3g
  Las Palmas v Ath Madrid              DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Sociedad v Barcelona                 BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Alaves v Almeria                     BTTS_OVER        BTTS                   H        1g
  Ath Madrid v Mallorca                BTTS_OVER        OVER_25                H        1g
  Las Palmas v Getafe                  BTTS_OVER        BTTS                   H        2g
  Real Madrid v Granada                BTTS_OVER        BTTS                   H        2g
  Almeria v Betis                      BTTS_OVER        BTTS                   D        0g
  Barcelona v Ath Madrid               BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Mallorca v Sevilla                   BTTS_OVER        BTTS                   H        1g
  Alaves v Las Palmas                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Vallecano v Celta                    BTTS_OVER        BTTS                   D        0g
  Celta v Granada                      BTTS_OVER        BTTS                   H        1g
  Ath Bilbao v Ath Madrid              BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Ath Madrid v Sevilla                 BTTS_OVER        BTTS                   H        1g
  Getafe v Vallecano                   AVOID            AVOID_VOLATILE         A        2g
  Osasuna v Almeria                    BTTS_OVER        BTTS                   H        1g
  Sevilla v Alaves                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        5g
  Almeria v Girona                     BTTS_OVER        BOTH_OVER25_BTTS       D        0g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Betis v Osasuna                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Vallecano v Sociedad                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        4g
  Ath Bilbao v Valencia                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Ath Madrid v Alaves                  DIRECTION        DIRECTION_HOME         H        3g
  Granada v Villarreal                 BTTS_OVER        BTTS                   A        5g
  Osasuna v Girona                     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        6g
  Celta v Sevilla                      BTTS_OVER        BTTS                   D        2g
  Almeria v Sociedad                   BTTS_OVER        BOTH_OVER25_BTTS       A        4g
  Granada v Getafe                     BTTS_OVER        BTTS                   D        2g
  Osasuna v Las Palmas                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Sevilla v Betis                      BTTS_OVER        BTTS                   D        2g
  Ath Madrid v Villarreal              BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  Barcelona v Alaves                   DIRECTION        DIRECTION_HOME         H        3g
  Alaves v Granada                     BTTS_OVER        BTTS                   H        4g
  Valencia v Celta                     AVOID            AVOID_VOLATILE         D        0g
  Getafe v Almeria                     BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Villarreal v Osasuna                 BTTS_OVER        BTTS                   H        4g
  Sociedad v Sevilla                   BTTS_OVER        BTTS                   H        3g
  Betis v Las Palmas                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Girona v Ath Bilbao                  BTTS_OVER        OVER_25                D        2g

## Sample Size Warnings

  ⚠ DIRECTION: only 13 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 13 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 3 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype OVER_25: only 6 evaluatable matches.

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