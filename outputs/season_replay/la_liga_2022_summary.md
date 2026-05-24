# Season Replay Audit — La Liga 2022

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 101
- Predictions with OK model : 280
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 280
- Evaluatable (type): 251
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     35    24   68.6%  
  BTTS_OVER                 68    45   66.2%  over25=36/68  btts=41/68
  DIRECTION                 12     8   66.7%    ⚠ n<20
  DOUBLE_CHANCE            108    77   71.3%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                     28    27   96.4%  

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            23    16   69.6%  BTTS_OVER
  BTTS                        39    20   51.3%  BTTS_OVER
  DIRECTION_AWAY               3     1   33.3%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               8     7   87.5%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            77    55   71.4%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            31    22   71.0%  DOUBLE_CHANCE
  OVER_25                      6     3   50.0%  BTTS_OVER  ⚠ n<20
  UNDER_35                    28    27   96.4%  UNDER

### BTTS_OVER Subtype Split

  Type-level OR : 45/68  (66.2%)
  Subtype BOTH_OVER25_BTTS      : 16/23  (69.6%)
  Subtype BTTS                  : 20/39  (51.3%)
  Subtype OVER_25               : 3/6  (50.0%)

### Best Performing Subtypes
  UNDER_35                 96.4%  (27/28)
  DIRECTION_HOME           87.5%  (7/8)
  DOUBLE_CHANCE_1X         71.4%  (55/77)
  DOUBLE_CHANCE_X2         71.0%  (22/31)
  BOTH_OVER25_BTTS         69.6%  (16/23)

### Worst Performing Subtypes
  DIRECTION_AWAY           33.3%  (1/3)
  OVER_25                  50.0%  (3/6)
  BTTS                     51.3%  (20/39)
  BOTH_OVER25_BTTS         69.6%  (16/23)
  DOUBLE_CHANCE_X2         71.0%  (22/31)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             23    15   65.2%
  low (3-5)              102    78   76.5%
  medium (5-7)           126    88   69.8%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               176   133   75.6%
  medium (4-6)            75    48   64.0%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                21    13   61.9%
  LOW                 62    44   71.0%
  MEDIUM             165   121   73.3%
  NO-CONFIDENCE        3     3  100.0%  ⚠ small sample

## Success by Season Phase

  early           23    14   60.9%
  mid            113    82   72.6%
  late           115    85   73.9%

## Success by Odds Bucket

  heavy_fav (<=1.5)               37    27   73.0%
  medium_fav (2.0-2.5)            88    63   71.6%
  no_clear_fav (>2.5)             19    16   84.2%  ⚠ small sample
  strong_fav (1.5-2.0)           107    75   70.1%

## AVOID Diagnostic

  Total AVOID calls  : 35
  Correctly avoided  : 24 / 35  (68.6%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 20/28
  Under 3.5 hit  : 27/28
  Type OR success: 27/28  (96.4%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Valladolid v Sociedad                DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        1g
  Valencia v Mallorca                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Valencia v Barcelona                 BTTS_OVER        OVER_25                A        1g
  Cadiz v Ath Madrid                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        5g
  Sevilla v Vallecano                  BTTS_OVER        BTTS                   A        1g
  Sociedad v Betis                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Elche v Getafe                       AVOID            AVOID_VOLATILE         A        1g
  Celta v Osasuna                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Barcelona v Almeria                  BTTS_OVER        OVER_25                H        2g
  Mallorca v Ath Madrid                BTTS_OVER        BTTS                   H        1g
  Vallecano v Celta                    BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Ath Madrid v Elche                   BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Valladolid v Real Madrid             BTTS_OVER        BTTS                   A        2g
  Elche v Celta                        BTTS_OVER        BTTS                   A        1g
  Valencia v Cadiz                     BTTS_OVER        BTTS                   A        1g
  Villarreal v Real Madrid             DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Getafe v Espanol                     AVOID            AVOID_VOLATILE         A        3g
  Sevilla v Cadiz                      BTTS_OVER        BTTS                   H        1g
  Villarreal v Girona                  BTTS_OVER        BTTS                   H        1g
  Girona v Barcelona                   BTTS_OVER        BTTS                   A        1g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Vallecano v Cadiz                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        6g
  Real Madrid v Sevilla                BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  Barcelona v Ath Bilbao               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Villarreal v Almeria                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Betis v Ath Madrid                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  Espanol v Elche                      BTTS_OVER        OVER_25                D        4g
  Girona v Osasuna                     BTTS_OVER        BTTS                   D        2g
  Celta v Getafe                       BTTS_OVER        OVER_25                D        2g
  Ath Bilbao v Villarreal              DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Osasuna v Valladolid                 UNDER            UNDER_35               H        2g
  Real Madrid v Girona                 BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Girona v Ath Bilbao                  BTTS_OVER        BTTS                   H        3g
  Valladolid v Elche                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Villarreal v Mallorca                UNDER            UNDER_35               A        2g
  Betis v Sevilla                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Ath Madrid v Espanol                 BTTS_OVER        BTTS                   D        2g
  Sociedad v Valencia                  BTTS_OVER        BTTS                   D        2g
  Vallecano v Real Madrid              BTTS_OVER        BOTH_OVER25_BTTS       H        5g
  Elche v Girona                       BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Ath Bilbao v Valladolid              DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g

## Sample Size Warnings

  ⚠ DIRECTION: only 12 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 3 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 8 evaluatable matches.
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