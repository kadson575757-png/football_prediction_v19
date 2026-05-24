# Season Replay Audit — Bundesliga 2024

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 64
- Predictions with OK model : 206
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 206
- Evaluatable (type): 175
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     30    23   76.7%  
  BTTS_OVER                 97    72   74.2%  over25=65/97  btts=58/97
  DIRECTION                  1     1  100.0%    ⚠ n<20
  DOUBLE_CHANCE             44    32   72.7%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      3     3  100.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            54    26   48.1%  BTTS_OVER
  BTTS                        26    16   61.5%  BTTS_OVER
  DIRECTION_HOME               1     1  100.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            34    25   73.5%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            10     7   70.0%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     17    10   58.8%  BTTS_OVER  ⚠ n<20
  UNDER_35                     3     3  100.0%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 72/97  (74.2%)
  Subtype BOTH_OVER25_BTTS      : 26/54  (48.1%)
  Subtype BTTS                  : 16/26  (61.5%)
  Subtype OVER_25               : 10/17  (58.8%)

### Best Performing Subtypes
  DIRECTION_HOME           100.0%  (1/1)
  UNDER_35                 100.0%  (3/3)
  DOUBLE_CHANCE_1X         73.5%  (25/34)
  DOUBLE_CHANCE_X2         70.0%  (7/10)
  BTTS                     61.5%  (16/26)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         48.1%  (26/54)
  OVER_25                  58.8%  (10/17)
  BTTS                     61.5%  (16/26)
  DOUBLE_CHANCE_X2         70.0%  (7/10)
  DOUBLE_CHANCE_1X         73.5%  (25/34)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             19    16   84.2%  ⚠ small sample
  low (3-5)               73    55   75.3%
  medium (5-7)            83    60   72.3%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)                58    45   77.6%
  medium (4-6)           117    86   73.5%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                15    13   86.7%  ⚠ small sample
  LOW                 43    31   72.1%
  MEDIUM             116    86   74.1%
  NO-CONFIDENCE        1     1  100.0%  ⚠ small sample

## Success by Season Phase

  early            2     1   50.0%  ⚠ small sample
  mid             85    66   77.6%
  late            88    64   72.7%

## Success by Odds Bucket

  heavy_fav (<=1.5)               35    28   80.0%
  medium_fav (2.0-2.5)            61    45   73.8%
  no_clear_fav (>2.5)             13     9   69.2%  ⚠ small sample
  strong_fav (1.5-2.0)            66    49   74.2%

## AVOID Diagnostic

  Total AVOID calls  : 30
  Correctly avoided  : 23 / 30  (76.7%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 3/3
  Under 3.5 hit  : 3/3
  Type OR success: 3/3  (100.0%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Augsburg v Bochum                    BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Mainz v Hoffenheim                   BTTS_OVER        BTTS                   H        2g
  Holstein Kiel v RB Leipzig           BTTS_OVER        OVER_25                A        2g
  Bochum v Werder Bremen               BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Mainz v Bayern Munich                DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Augsburg v Leverkusen                BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Heidenheim v Union Berlin            DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        2g
  Hoffenheim v Wolfsburg               AVOID            AVOID_VOLATILE         A        1g
  St Pauli v Ein Frankfurt             BTTS_OVER        OVER_25                A        1g
  M'gladbach v Bayern Munich           BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Augsburg v Stuttgart                 BTTS_OVER        BTTS                   A        1g
  Leverkusen v Mainz                   BTTS_OVER        BTTS                   H        1g
  Union Berlin v Augsburg              DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Ein Frankfurt v Dortmund             BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Heidenheim v St Pauli                AVOID            AVOID_VOLATILE         A        2g
  Freiburg v Heidenheim                BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Wolfsburg v Leverkusen               BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Bochum v Dortmund                    DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        2g
  St Pauli v Freiburg                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Holstein Kiel v Leverkusen           BTTS_OVER        BOTH_OVER25_BTTS       A        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Freiburg v M'gladbach                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Union Berlin v Leverkusen            BTTS_OVER        BTTS                   A        3g
  Werder Bremen v Stuttgart            AVOID            AVOID_VOLATILE         D        4g
  Dortmund v Bayern Munich             BTTS_OVER        OVER_25                D        2g
  Heidenheim v Ein Frankfurt           BTTS_OVER        BOTH_OVER25_BTTS       A        4g
  M'gladbach v Dortmund                AVOID            AVOID_VOLATILE         D        2g
  Leverkusen v St Pauli                BTTS_OVER        BTTS                   H        3g
  Ein Frankfurt v Augsburg             BTTS_OVER        BOTH_OVER25_BTTS       D        4g
  Bayern Munich v Heidenheim           BTTS_OVER        OVER_25                H        6g
  Wolfsburg v Mainz                    AVOID            AVOID_VOLATILE         H        7g
  Hoffenheim v Freiburg                AVOID            AVOID_VOLATILE         D        2g
  Freiburg v Wolfsburg                 BTTS_OVER        BOTH_OVER25_BTTS       H        5g
  M'gladbach v Holstein Kiel           BTTS_OVER        BTTS                   H        5g
  Heidenheim v Stuttgart               BTTS_OVER        OVER_25                A        4g
  Dortmund v Hoffenheim                BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  RB Leipzig v Ein Frankfurt           AVOID            AVOID_VOLATILE         H        3g
  Bayern Munich v RB Leipzig           BTTS_OVER        OVER_25                H        6g
  Leverkusen v Freiburg                BTTS_OVER        BTTS                   H        6g
  Werder Bremen v Union Berlin         DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        5g
  Holstein Kiel v Augsburg             BTTS_OVER        OVER_25                H        6g

## Sample Size Warnings

  ⚠ DIRECTION: only 1 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 3 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 1 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype UNDER_35: only 3 evaluatable matches.

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