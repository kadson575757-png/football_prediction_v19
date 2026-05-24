# Season Replay Audit — Belgian Pro League 2024

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 109
- Predictions with OK model : 274
- Predictions with no model : 18

- Mode              : walk_forward
- Total matches     : 292
- Evaluatable (type): 257
- Data-warning rows : 22

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     35    29   82.9%  
  BTTS_OVER                123    86   69.9%  over25=71/123  btts=75/123
  DIRECTION                  4     2   50.0%    ⚠ n<20
  DOUBLE_CHANCE             84    70   83.3%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                     11     8   72.7%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            29    14   48.3%  BTTS_OVER
  BTTS                        68    42   61.8%  BTTS_OVER
  DIRECTION_HOME               3     2   66.7%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            67    54   80.6%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            17    16   94.1%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     26    15   57.7%  BTTS_OVER
  UNDER_35                    11     8   72.7%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 86/123  (69.9%)
  Subtype BOTH_OVER25_BTTS      : 14/29  (48.3%)
  Subtype BTTS                  : 42/68  (61.8%)
  Subtype OVER_25               : 15/26  (57.7%)

### Best Performing Subtypes
  DOUBLE_CHANCE_X2         94.1%  (16/17)
  DOUBLE_CHANCE_1X         80.6%  (54/67)
  UNDER_35                 72.7%  (8/11)
  DIRECTION_HOME           66.7%  (2/3)
  BTTS                     61.8%  (42/68)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         48.3%  (14/29)
  OVER_25                  57.7%  (15/26)
  BTTS                     61.8%  (42/68)
  DIRECTION_HOME           66.7%  (2/3)
  UNDER_35                 72.7%  (8/11)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             22    18   81.8%
  low (3-5)              104    78   75.0%
  medium (5-7)           120    91   75.8%
  very_low (<3)           11     8   72.7%  ⚠ small sample

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               118    95   80.5%
  medium (4-6)           139   100   71.9%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                18    15   83.3%  ⚠ small sample
  LOW                 73    55   75.3%
  MEDIUM             162   121   74.7%
  NO-CONFIDENCE        4     4  100.0%  ⚠ small sample

## Success by Season Phase

  early           80    58   72.5%
  mid             89    70   78.7%
  late            88    67   76.1%

## Success by Odds Bucket

  heavy_fav (<=1.5)               34    28   82.4%
  medium_fav (2.0-2.5)            91    68   74.7%
  no_clear_fav (>2.5)             16    13   81.2%  ⚠ small sample
  strong_fav (1.5-2.0)           116    86   74.1%

## AVOID Diagnostic

  Total AVOID calls  : 35
  Correctly avoided  : 29 / 35  (82.9%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 5/11
  Under 3.5 hit  : 8/11
  Type OR success: 8/11  (72.7%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  St. Gilloise v Charleroi             AVOID            AVOID_VOLATILE         H        1g
  Club Brugge v Antwerp                BTTS_OVER        BTTS                   H        1g
  Antwerp v Mechelen                   BTTS_OVER        BTTS                   A        1g
  Standard v Beerschot VA              AVOID            AVOID_VOLATILE         H        1g
  St Truiden v St. Gilloise            BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Charleroi v Kortrijk                 AVOID            AVOID_VOLATILE         H        1g
  Mechelen v Charleroi                 UNDER            UNDER_35               H        7g
  St. Gilloise v Anderlecht            BTTS_OVER        BTTS                   D        0g
  Dender v Standard                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Gent v Mechelen                      BTTS_OVER        BTTS                   H        2g
  Beerschot VA v St Truiden            AVOID            AVOID_VOLATILE         A        3g
  Club Brugge v Gent                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        6g
  Mechelen v Cercle Brugge             BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Cercle Brugge v Dender               BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Kortrijk v Beerschot VA              BTTS_OVER        OVER_25                H        1g
  Charleroi v Oud-Heverlee Leuven      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  St Truiden v Westerlo                AVOID            AVOID_VOLATILE         H        2g
  Gent v Genk                          BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  St. Gilloise v Cercle Brugge         DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        4g
  Westerlo v Dender                    BTTS_OVER        BOTH_OVER25_BTTS       H        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Genk v Club Brugge                   AVOID            AVOID_VOLATILE         H        5g
  Antwerp v St Truiden                 AVOID            AVOID_VOLATILE         H        7g
  Charleroi v Gent                     AVOID            AVOID_VOLATILE         H        1g
  Cercle Brugge v Beerschot VA         BTTS_OVER        OVER_25                H        5g
  Beerschot VA v Genk                  BTTS_OVER        BOTH_OVER25_BTTS       A        7g
  St Truiden v Dender                  BTTS_OVER        BOTH_OVER25_BTTS       D        6g
  Mechelen v Anderlecht                BTTS_OVER        BTTS                   A        4g
  Gent v Westerlo                      BTTS_OVER        OVER_25                H        5g
  Kortrijk v Standard                  AVOID            AVOID_VOLATILE         H        1g
  Oud-Heverlee Leuven v Cercle Brugg   BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Westerlo v Oud-Heverlee Leuven       BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Dender v Club Brugge                 BTTS_OVER        BTTS                   A        3g
  Genk v Westerlo                      AVOID            AVOID_VOLATILE         H        1g
  Beerschot VA v Dender                BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Oud-Heverlee Leuven v Standard       UNDER            UNDER_35               H        2g
  Club Brugge v Cercle Brugge          BTTS_OVER        BTTS                   H        3g
  Gent v Antwerp                       AVOID            AVOID_VOLATILE         D        2g
  Kortrijk v St Truiden                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Anderlecht v Westerlo                BTTS_OVER        BTTS                   D        4g
  Cercle Brugge v Genk                 BTTS_OVER        BOTH_OVER25_BTTS       A        5g

## Sample Size Warnings

  ⚠ DIRECTION: only 4 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 11 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 3 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.

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