# Season Replay Audit — 2. Bundesliga 2022

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
- Evaluatable (type): 179
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     27    22   81.5%  
  BTTS_OVER                 90    58   64.4%  over25=50/90  btts=49/90
  DIRECTION                  3     1   33.3%    ⚠ n<20
  DOUBLE_CHANCE             55    40   72.7%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      4     3   75.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            32    13   40.6%  BTTS_OVER
  BTTS                        47    27   57.4%  BTTS_OVER
  DIRECTION_HOME               3     1   33.3%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            46    36   78.3%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2             9     4   44.4%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     11     4   36.4%  BTTS_OVER  ⚠ n<20
  UNDER_35                     4     3   75.0%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 58/90  (64.4%)
  Subtype BOTH_OVER25_BTTS      : 13/32  (40.6%)
  Subtype BTTS                  : 27/47  (57.4%)
  Subtype OVER_25               : 4/11  (36.4%)

### Best Performing Subtypes
  DOUBLE_CHANCE_1X         78.3%  (36/46)
  UNDER_35                 75.0%  (3/4)
  BTTS                     57.4%  (27/47)
  DOUBLE_CHANCE_X2         44.4%  (4/9)
  BOTH_OVER25_BTTS         40.6%  (13/32)

### Worst Performing Subtypes
  DIRECTION_HOME           33.3%  (1/3)
  OVER_25                  36.4%  (4/11)
  BOTH_OVER25_BTTS         40.6%  (13/32)
  DOUBLE_CHANCE_X2         44.4%  (4/9)
  BTTS                     57.4%  (27/47)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)              5     2   40.0%  ⚠ small sample
  low (3-5)               98    67   68.4%
  medium (5-7)            76    55   72.4%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              3     2   66.7%  ⚠ small sample
  low (<4)                77    56   72.7%
  medium (4-6)            99    66   66.7%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                 4     1   25.0%  ⚠ small sample
  LOW                 45    36   80.0%
  MEDIUM             128    85   66.4%
  NO-CONFIDENCE        2     2  100.0%  ⚠ small sample

## Success by Season Phase

  early            1     0    0.0%  ⚠ small sample
  mid             87    60   69.0%
  late            91    64   70.3%

## Success by Odds Bucket

  heavy_fav (<=1.5)               11     6   54.5%  ⚠ small sample
  medium_fav (2.0-2.5)            87    59   67.8%
  no_clear_fav (>2.5)             12     7   58.3%  ⚠ small sample
  strong_fav (1.5-2.0)            69    52   75.4%

## AVOID Diagnostic

  Total AVOID calls  : 27
  Correctly avoided  : 22 / 27  (81.5%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 3/4
  Under 3.5 hit  : 3/4
  Type OR success: 3/4  (75.0%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Fortuna Dusseldorf v Nurnberg        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Magdeburg v Braunschweig             BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Hannover v Bielefeld                 BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Hansa Rostock v Kaiserslautern       BTTS_OVER        BTTS                   A        2g
  Bielefeld v St Pauli                 BTTS_OVER        BTTS                   H        2g
  Braunschweig v Paderborn             BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Hamburg v Magdeburg                  DIRECTION        DIRECTION_HOME         A        5g
  Karlsruhe v Fortuna Dusseldorf       AVOID            AVOID_VOLATILE         A        2g
  Greuther Furth v Bielefeld           BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Regensburg v Hansa Rostock           DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Darmstadt v Hannover                 BTTS_OVER        BTTS                   H        1g
  Braunschweig v Greuther Furth        BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Nurnberg v Magdeburg                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Hannover v Fortuna Dusseldorf        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        2g
  Paderborn v Bielefeld                BTTS_OVER        OVER_25                A        2g
  St Pauli v Holstein Kiel             BTTS_OVER        BTTS                   D        0g
  Greuther Furth v Hamburg             BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Magdeburg v Darmstadt                BTTS_OVER        BTTS                   A        1g
  Fortuna Dusseldorf v Kaiserslauter   AVOID            AVOID_VOLATILE         A        3g
  Braunschweig v Hansa Rostock         AVOID            AVOID_VOLATILE         A        1g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Holstein Kiel v Heidenheim           AVOID            AVOID_VOLATILE         H        4g
  Paderborn v Sandhausen               BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Darmstadt v Holstein Kiel            BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Regensburg v Sandhausen              AVOID            AVOID_VOLATILE         H        3g
  Nurnberg v Hannover                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        0g
  Heidenheim v Greuther Furth          BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  Magdeburg v Heidenheim               BTTS_OVER        OVER_25                D        2g
  Kaiserslautern v Nurnberg            DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        0g
  Holstein Kiel v Fortuna Dusseldorf   BTTS_OVER        BTTS                   A        3g
  Hannover v Karlsruhe                 AVOID            AVOID_VOLATILE         H        1g
  Paderborn v Hamburg                  AVOID            AVOID_VOLATILE         A        5g
  Sandhausen v Braunschweig            BTTS_OVER        BTTS                   D        4g
  Karlsruhe v Holstein Kiel            AVOID            AVOID_VOLATILE         A        5g
  Bielefeld v Kaiserslautern           BTTS_OVER        BTTS                   A        5g
  Heidenheim v Paderborn               BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Hamburg v Regensburg                 BTTS_OVER        OVER_25                H        4g
  Sandhausen v Heidenheim              BTTS_OVER        BTTS                   A        7g
  Regensburg v Braunschweig            AVOID            AVOID_VOLATILE         D        2g
  Hansa Rostock v Nurnberg             AVOID            AVOID_VOLATILE         D        2g
  Holstein Kiel v Hannover             BTTS_OVER        BTTS                   D        2g

## Sample Size Warnings

  ⚠ DIRECTION: only 3 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 4 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 3 evaluatable matches.
  ⚠ subtype DOUBLE_CHANCE_X2: only 9 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype UNDER_35: only 4 evaluatable matches.

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