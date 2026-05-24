# Season Replay Audit — La Liga 2025

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 112
- Predictions with OK model : 290
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 290
- Evaluatable (type): 249
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     33    28   84.8%  
  BTTS_OVER                130    85   65.4%  over25=69/130  btts=77/130
  DIRECTION                  6     5   83.3%    ⚠ n<20
  DOUBLE_CHANCE             74    56   75.7%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      6     5   83.3%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            50    28   56.0%  BTTS_OVER
  BTTS                        75    43   57.3%  BTTS_OVER
  DIRECTION_HOME               6     5   83.3%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            48    35   72.9%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            26    21   80.8%  DOUBLE_CHANCE
  OVER_25                      5     3   60.0%  BTTS_OVER  ⚠ n<20
  UNDER_35                     6     5   83.3%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 85/130  (65.4%)
  Subtype BOTH_OVER25_BTTS      : 28/50  (56.0%)
  Subtype BTTS                  : 43/75  (57.3%)
  Subtype OVER_25               : 3/5  (60.0%)

### Best Performing Subtypes
  DIRECTION_HOME           83.3%  (5/6)
  UNDER_35                 83.3%  (5/6)
  DOUBLE_CHANCE_X2         80.8%  (21/26)
  DOUBLE_CHANCE_1X         72.9%  (35/48)
  OVER_25                  60.0%  (3/5)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         56.0%  (28/50)
  BTTS                     57.3%  (43/75)
  OVER_25                  60.0%  (3/5)
  DOUBLE_CHANCE_1X         72.9%  (35/48)
  DOUBLE_CHANCE_X2         80.8%  (21/26)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             27    21   77.8%
  low (3-5)              116    85   73.3%
  medium (5-7)           106    73   68.9%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              1     1  100.0%  ⚠ small sample
  low (<4)               103    79   76.7%
  medium (4-6)           145    99   68.3%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                24    18   75.0%
  LOW                 63    46   73.0%
  MEDIUM             160   114   71.2%
  NO-CONFIDENCE        2     1   50.0%  ⚠ small sample

## Success by Season Phase

  early           36    29   80.6%
  mid            104    75   72.1%
  late           109    75   68.8%

## Success by Odds Bucket

  heavy_fav (<=1.5)               37    28   75.7%
  medium_fav (2.0-2.5)           102    75   73.5%
  no_clear_fav (>2.5)             27    18   66.7%
  strong_fav (1.5-2.0)            83    58   69.9%

## AVOID Diagnostic

  Total AVOID calls  : 33
  Correctly avoided  : 28 / 33  (84.8%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 5/6
  Under 3.5 hit  : 5/6
  Type OR success: 5/6  (83.3%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Ath Madrid v Osasuna                 BTTS_OVER        BTTS                   H        1g
  Elche v Ath Bilbao                   BTTS_OVER        BTTS                   D        0g
  Getafe v Real Madrid                 BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Ath Bilbao v Getafe                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Espanol v Elche                      BTTS_OVER        BTTS                   H        1g
  Betis v Ath Madrid                   BTTS_OVER        BTTS                   A        2g
  Mallorca v Getafe                    BTTS_OVER        BTTS                   H        1g
  Alaves v Celta                       BTTS_OVER        BTTS                   A        1g
  Celta v Espanol                      BTTS_OVER        BTTS                   A        1g
  Sevilla v Betis                      BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Alaves v Sociedad                    BTTS_OVER        BTTS                   H        1g
  Ath Bilbao v Ath Madrid              DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        1g
  Real Madrid v Celta                  BTTS_OVER        BTTS                   A        2g
  Barcelona v Osasuna                  BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Getafe v Espanol                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Villarreal v Barcelona               BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Betis v Getafe                       UNDER            UNDER_35               H        4g
  Ath Bilbao v Espanol                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Espanol v Barcelona                  BTTS_OVER        OVER_25                A        2g
  Mallorca v Girona                    AVOID            AVOID_VOLATILE         A        3g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Oviedo v Espanol                     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        2g
  Sevilla v Mallorca                   BTTS_OVER        BOTH_OVER25_BTTS       A        4g
  Barcelona v Girona                   BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Villarreal v Betis                   BTTS_OVER        BTTS                   D        4g
  Celta v Sociedad                     BTTS_OVER        BTTS                   D        2g
  Levante v Vallecano                  AVOID            AVOID_VOLATILE         A        3g
  Alaves v Valencia                    AVOID            AVOID_VOLATILE         D        0g
  Sociedad v Sevilla                   BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Girona v Oviedo                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        6g
  Mallorca v Levante                   BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Real Madrid v Barcelona              BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Osasuna v Celta                      BTTS_OVER        BTTS                   A        5g
  Vallecano v Alaves                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Sociedad v Ath Bilbao                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        5g
  Ath Madrid v Sevilla                 BTTS_OVER        BTTS                   H        3g
  Villarreal v Vallecano               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Levante v Celta                      BTTS_OVER        BTTS                   A        3g
  Barcelona v Elche                    BTTS_OVER        BTTS                   H        4g
  Betis v Mallorca                     BTTS_OVER        BTTS                   H        3g
  Oviedo v Osasuna                     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        0g

## Sample Size Warnings

  ⚠ DIRECTION: only 6 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 6 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 6 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype OVER_25: only 5 evaluatable matches.
  ⚠ subtype UNDER_35: only 6 evaluatable matches.

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