# Season Replay Audit — Eredivisie 2024

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 67
- Predictions with OK model : 203
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 203
- Evaluatable (type): 175
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     22    18   81.8%  
  BTTS_OVER                108    75   69.4%  over25=65/108  btts=64/108
  DIRECTION                  3     3  100.0%    ⚠ n<20
  DOUBLE_CHANCE             41    30   73.2%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      1     1  100.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            43    21   48.8%  BTTS_OVER
  BTTS                        43    27   62.8%  BTTS_OVER
  DIRECTION_AWAY               2     2  100.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               1     1  100.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            28    22   78.6%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            13     8   61.5%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     22    15   68.2%  BTTS_OVER
  UNDER_35                     1     1  100.0%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 75/108  (69.4%)
  Subtype BOTH_OVER25_BTTS      : 21/43  (48.8%)
  Subtype BTTS                  : 27/43  (62.8%)
  Subtype OVER_25               : 15/22  (68.2%)

### Best Performing Subtypes
  DIRECTION_AWAY           100.0%  (2/2)
  DIRECTION_HOME           100.0%  (1/1)
  UNDER_35                 100.0%  (1/1)
  DOUBLE_CHANCE_1X         78.6%  (22/28)
  OVER_25                  68.2%  (15/22)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         48.8%  (21/43)
  DOUBLE_CHANCE_X2         61.5%  (8/13)
  BTTS                     62.8%  (27/43)
  OVER_25                  68.2%  (15/22)
  DOUBLE_CHANCE_1X         78.6%  (22/28)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             24    16   66.7%
  low (3-5)               56    39   69.6%
  medium (5-7)            95    72   75.8%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)                56    41   73.2%
  medium (4-6)           119    86   72.3%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                22    16   72.7%
  LOW                 35    22   62.9%
  MEDIUM             115    86   74.8%
  NO-CONFIDENCE        3     3  100.0%  ⚠ small sample

## Success by Season Phase

  mid             89    65   73.0%
  late            86    62   72.1%

## Success by Odds Bucket

  heavy_fav (<=1.5)               47    35   74.5%
  medium_fav (2.0-2.5)            50    33   66.0%
  no_clear_fav (>2.5)              9     7   77.8%  ⚠ small sample
  strong_fav (1.5-2.0)            69    52   75.4%

## AVOID Diagnostic

  Total AVOID calls  : 22
  Correctly avoided  : 18 / 22  (81.8%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 1/1
  Under 3.5 hit  : 1/1
  Type OR success: 1/1  (100.0%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  AZ Alkmaar v Willem II               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Ajax v Zwolle                        BTTS_OVER        BTTS                   H        2g
  Nijmegen v Utrecht                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Zwolle v Sparta Rotterdam            AVOID            AVOID_VOLATILE         H        1g
  AZ Alkmaar v Heracles                BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Sparta Rotterdam v NAC Breda         DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Willem II v Heerenveen               AVOID            AVOID_VOLATILE         A        3g
  Zwolle v Willem II                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Heerenveen v PSV Eindhoven           BTTS_OVER        OVER_25                H        1g
  Twente v Groningen                   BTTS_OVER        OVER_25                H        2g
  AZ Alkmaar v Twente                  BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Almere City v Heerenveen             DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Sparta Rotterdam v Ajax              BTTS_OVER        BTTS                   A        2g
  Willem II v Nijmegen                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        5g
  Utrecht v AZ Alkmaar                 BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Almere City v Heracles               AVOID            AVOID_VOLATILE         A        2g
  Heerenveen v Ajax                    BTTS_OVER        OVER_25                A        2g
  Willem II v AZ Alkmaar               BTTS_OVER        BTTS                   A        2g
  Groningen v Nijmegen                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  For Sittard v Ajax                   BTTS_OVER        BOTH_OVER25_BTTS       A        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Twente v Ajax                        AVOID            AVOID_VOLATILE         D        4g
  Go Ahead Eagles v Almere City        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Heracles v Waalwijk                  BTTS_OVER        OVER_25                D        4g
  For Sittard v Twente                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  PSV Eindhoven v Groningen            BTTS_OVER        OVER_25                H        5g
  Willem II v NAC Breda                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Sparta Rotterdam v AZ Alkmaar        BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Heerenveen v Waalwijk                BTTS_OVER        OVER_25                D        2g
  NAC Breda v Almere City              DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Groningen v Willem II                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Nijmegen v Ajax                      DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  Twente v Go Ahead Eagles             BTTS_OVER        OVER_25                H        5g
  Utrecht v PSV Eindhoven              BTTS_OVER        OVER_25                A        7g
  Ajax v Utrecht                       BTTS_OVER        BTTS                   D        4g
  PSV Eindhoven v Twente               BTTS_OVER        OVER_25                H        7g
  Go Ahead Eagles v Nijmegen           BTTS_OVER        OVER_25                H        5g
  Waalwijk v Feyenoord                 BTTS_OVER        BTTS                   A        5g
  Groningen v Zwolle                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        0g
  AZ Alkmaar v Ajax                    BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  For Sittard v Waalwijk               BTTS_OVER        BTTS                   H        5g

## Sample Size Warnings

  ⚠ DIRECTION: only 3 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 1 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 2 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 1 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype UNDER_35: only 1 evaluatable matches.

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