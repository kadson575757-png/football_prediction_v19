# Season Replay Audit — 2. Bundesliga 2024

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 65
- Predictions with OK model : 205
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 205
- Evaluatable (type): 176
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     31    28   90.3%  
  BTTS_OVER                 97    63   64.9%  over25=54/97  btts=52/97
  DOUBLE_CHANCE             46    33   71.7%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      2     0    0.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            48    23   47.9%  BTTS_OVER
  BTTS                        37    18   48.6%  BTTS_OVER
  DOUBLE_CHANCE_1X            30    21   70.0%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            16    12   75.0%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     12     6   50.0%  BTTS_OVER  ⚠ n<20
  UNDER_35                     2     0    0.0%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 63/97  (64.9%)
  Subtype BOTH_OVER25_BTTS      : 23/48  (47.9%)
  Subtype BTTS                  : 18/37  (48.6%)
  Subtype OVER_25               : 6/12  (50.0%)

### Best Performing Subtypes
  DOUBLE_CHANCE_X2         75.0%  (12/16)
  DOUBLE_CHANCE_1X         70.0%  (21/30)
  OVER_25                  50.0%  (6/12)
  BTTS                     48.6%  (18/37)
  BOTH_OVER25_BTTS         47.9%  (23/48)

### Worst Performing Subtypes
  UNDER_35                 0.0%  (0/2)
  BOTH_OVER25_BTTS         47.9%  (23/48)
  BTTS                     48.6%  (18/37)
  OVER_25                  50.0%  (6/12)
  DOUBLE_CHANCE_1X         70.0%  (21/30)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (3-5)               81    64   79.0%
  medium (5-7)            95    60   63.2%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              3     2   66.7%  ⚠ small sample
  low (<4)                52    37   71.2%
  medium (4-6)           121    85   70.2%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  LOW                 42    31   73.8%
  MEDIUM             131    90   68.7%
  NO-CONFIDENCE        3     3  100.0%  ⚠ small sample

## Success by Season Phase

  early            1     0    0.0%  ⚠ small sample
  mid             89    65   73.0%
  late            86    59   68.6%

## Success by Odds Bucket

  heavy_fav (<=1.5)               11     9   81.8%  ⚠ small sample
  medium_fav (2.0-2.5)            78    56   71.8%
  no_clear_fav (>2.5)              7     4   57.1%  ⚠ small sample
  strong_fav (1.5-2.0)            80    55   68.8%

## AVOID Diagnostic

  Total AVOID calls  : 31
  Correctly avoided  : 28 / 31  (90.3%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 0/2
  Under 3.5 hit  : 0/2
  Type OR success: 0/2  (0.0%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  FC Koln v Greuther Furth             BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Magdeburg v Ulm                      BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Elversberg v Hannover                DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        4g
  Schalke 04 v Regensburg              BTTS_OVER        OVER_25                H        2g
  Preußen Münster v FC Koln            BTTS_OVER        BTTS                   A        1g
  Regensburg v Magdeburg               BTTS_OVER        OVER_25                A        1g
  Darmstadt v Preußen Münster          BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Greuther Furth v Hannover            AVOID            AVOID_VOLATILE         H        1g
  Preußen Münster v Ulm                BTTS_OVER        BTTS                   D        0g
  Nurnberg v Braunschweig              BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Regensburg v Hannover                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Hamburg v FC Koln                    BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Paderborn v Hertha                   AVOID            AVOID_VOLATILE         A        3g
  Darmstadt v Paderborn                BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Nurnberg v Darmstadt                 BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Braunschweig v FC Koln               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Regensburg v Hertha                  BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Hertha v Kaiserslautern              BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Karlsruhe v Braunschweig             BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Paderborn v Preußen Münster          BTTS_OVER        BTTS                   H        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Darmstadt v Hertha                   AVOID            AVOID_VOLATILE         H        4g
  Fortuna Dusseldorf v Paderborn       BTTS_OVER        OVER_25                D        2g
  Karlsruhe v Preußen Münster          BTTS_OVER        BTTS                   D        2g
  Hamburg v Schalke 04                 BTTS_OVER        BOTH_OVER25_BTTS       D        4g
  Hannover v Darmstadt                 BTTS_OVER        BTTS                   A        3g
  Hertha v Ulm                         DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Greuther Furth v Karlsruhe           BTTS_OVER        BOTH_OVER25_BTTS       A        5g
  Magdeburg v Hertha                   AVOID            AVOID_VOLATILE         A        4g
  Schalke 04 v Kaiserslautern          BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Braunschweig v Regensburg            DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        0g
  Elversberg v Paderborn               AVOID            AVOID_VOLATILE         A        4g
  Karlsruhe v Hamburg                  AVOID            AVOID_VOLATILE         A        4g
  Ulm v Greuther Furth                 AVOID            AVOID_VOLATILE         D        2g
  Elversberg v Nurnberg                AVOID            AVOID_VOLATILE         H        3g
  Paderborn v Schalke 04               BTTS_OVER        BOTH_OVER25_BTTS       A        6g
  Preußen Münster v Magdeburg          BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Kaiserslautern v Karlsruhe           BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  Hannover v Ulm                       BTTS_OVER        BTTS                   H        5g
  Greuther Furth v Hertha              BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Hamburg v Darmstadt                  BTTS_OVER        BOTH_OVER25_BTTS       D        4g

## Sample Size Warnings

  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 2 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype UNDER_35: only 2 evaluatable matches.

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