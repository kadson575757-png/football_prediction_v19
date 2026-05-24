# Season Replay Audit — 2. Bundesliga 2023

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 66
- Predictions with OK model : 205
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 205
- Evaluatable (type): 188
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     32    28   87.5%  
  BTTS_OVER                114    78   68.4%  over25=65/114  btts=62/114
  DIRECTION                  1     1  100.0%    ⚠ n<20
  DOUBLE_CHANCE             41    31   75.6%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            70    32   45.7%  BTTS_OVER
  BTTS                        32    16   50.0%  BTTS_OVER
  DIRECTION_HOME               1     1  100.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            29    22   75.9%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            12     9   75.0%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     12     6   50.0%  BTTS_OVER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 78/114  (68.4%)
  Subtype BOTH_OVER25_BTTS      : 32/70  (45.7%)
  Subtype BTTS                  : 16/32  (50.0%)
  Subtype OVER_25               : 6/12  (50.0%)

### Best Performing Subtypes
  DIRECTION_HOME           100.0%  (1/1)
  DOUBLE_CHANCE_1X         75.9%  (22/29)
  DOUBLE_CHANCE_X2         75.0%  (9/12)
  BTTS                     50.0%  (16/32)
  OVER_25                  50.0%  (6/12)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         45.7%  (32/70)
  BTTS                     50.0%  (16/32)
  OVER_25                  50.0%  (6/12)
  DOUBLE_CHANCE_X2         75.0%  (9/12)
  DOUBLE_CHANCE_1X         75.9%  (22/29)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)              6     3   50.0%  ⚠ small sample
  low (3-5)               93    71   76.3%
  medium (5-7)            89    64   71.9%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              2     2  100.0%  ⚠ small sample
  low (<4)                54    42   77.8%
  medium (4-6)           132    94   71.2%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                 6     3   50.0%  ⚠ small sample
  LOW                 48    40   83.3%
  MEDIUM             128    90   70.3%
  NO-CONFIDENCE        6     5   83.3%  ⚠ small sample

## Success by Season Phase

  early            1     0    0.0%  ⚠ small sample
  mid             99    73   73.7%
  late            88    65   73.9%

## Success by Odds Bucket

  heavy_fav (<=1.5)               12     8   66.7%  ⚠ small sample
  medium_fav (2.0-2.5)            96    72   75.0%
  no_clear_fav (>2.5)              7     7  100.0%  ⚠ small sample
  strong_fav (1.5-2.0)            73    51   69.9%

## AVOID Diagnostic

  Total AVOID calls  : 32
  Correctly avoided  : 28 / 32  (87.5%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Kaiserslautern v Greuther Furth      BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Hamburg v Magdeburg                  BTTS_OVER        BTTS                   H        2g
  Hannover v Braunschweig              BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Hansa Rostock v Hertha               BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  St Pauli v Hannover                  BTTS_OVER        BTTS                   D        0g
  Holstein Kiel v Hamburg              DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        6g
  Greuther Furth v Fortuna Dusseldor   BTTS_OVER        BTTS                   H        1g
  Osnabruck v Magdeburg                BTTS_OVER        BTTS                   A        2g
  Paderborn v Hannover                 BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Wehen v Braunschweig                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        4g
  Elversberg v Nurnberg                BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Fortuna Dusseldorf v Holstein Kiel   AVOID            AVOID_VOLATILE         A        1g
  Hansa Rostock v Schalke 04           BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Hertha v Osnabruck                   BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Nurnberg v Hamburg                   BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  St Pauli v Kaiserslautern            BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Schalke 04 v Hamburg                 BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Paderborn v Greuther Furth           AVOID            AVOID_VOLATILE         A        1g
  Magdeburg v Wehen                    BTTS_OVER        BTTS                   H        1g
  Osnabruck v Paderborn                BTTS_OVER        OVER_25                D        0g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Nurnberg v Schalke 04                BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Osnabruck v Holstein Kiel            AVOID            AVOID_VOLATILE         D        2g
  Karlsruhe v Paderborn                BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Schalke 04 v Elversberg              BTTS_OVER        BTTS                   A        3g
  Paderborn v Nurnberg                 BTTS_OVER        BOTH_OVER25_BTTS       A        4g
  Hertha v Karlsruhe                   BTTS_OVER        OVER_25                D        4g
  Braunschweig v Osnabruck             AVOID            AVOID_VOLATILE         H        5g
  Magdeburg v Hansa Rostock            BTTS_OVER        BTTS                   A        3g
  Wehen v Kaiserslautern               BTTS_OVER        BTTS                   H        3g
  Hannover v Hertha                    AVOID            AVOID_VOLATILE         D        4g
  Fortuna Dusseldorf v Schalke 04      BTTS_OVER        BOTH_OVER25_BTTS       H        8g
  Hansa Rostock v St Pauli             BTTS_OVER        BTTS                   A        5g
  Elversberg v Paderborn               BTTS_OVER        BOTH_OVER25_BTTS       H        5g
  Greuther Furth v Wehen               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Kaiserslautern v Holstein Kiel       BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Karlsruhe v Nurnberg                 AVOID            AVOID_VOLATILE         H        5g
  Schalke 04 v Osnabruck               BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  St Pauli v Hamburg                   BTTS_OVER        BTTS                   D        4g
  Nurnberg v Fortuna Dusseldorf        AVOID            AVOID_VOLATILE         A        5g
  Magdeburg v Kaiserslautern           BTTS_OVER        BOTH_OVER25_BTTS       H        5g

## Sample Size Warnings

  ⚠ DIRECTION: only 1 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 1 evaluatable matches.
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