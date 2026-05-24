# Season Replay Audit — Serie A 2023

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 104
- Predictions with OK model : 280
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 280
- Evaluatable (type): 219
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     26    23   88.5%  
  BTTS_OVER                 86    59   68.6%  over25=52/86  btts=49/86
  DIRECTION                  7     7  100.0%    ⚠ n<20
  DOUBLE_CHANCE             94    78   83.0%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      6     5   83.3%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            26    12   46.2%  BTTS_OVER
  BTTS                        47    27   57.4%  BTTS_OVER
  DIRECTION_AWAY               4     4  100.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               2     2  100.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            61    52   85.2%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            33    26   78.8%  DOUBLE_CHANCE
  OVER_25                     13     8   61.5%  BTTS_OVER  ⚠ n<20
  UNDER_35                     6     5   83.3%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 59/86  (68.6%)
  Subtype BOTH_OVER25_BTTS      : 12/26  (46.2%)
  Subtype BTTS                  : 27/47  (57.4%)
  Subtype OVER_25               : 8/13  (61.5%)

### Best Performing Subtypes
  DIRECTION_AWAY           100.0%  (4/4)
  DIRECTION_HOME           100.0%  (2/2)
  DOUBLE_CHANCE_1X         85.2%  (52/61)
  UNDER_35                 83.3%  (5/6)
  DOUBLE_CHANCE_X2         78.8%  (26/33)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         46.2%  (12/26)
  BTTS                     57.4%  (27/47)
  OVER_25                  61.5%  (8/13)
  DOUBLE_CHANCE_X2         78.8%  (26/33)
  UNDER_35                 83.3%  (5/6)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             20    17   85.0%
  low (3-5)               95    69   72.6%
  medium (5-7)           104    86   82.7%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               120   102   85.0%
  medium (4-6)            99    70   70.7%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                18    15   83.3%  ⚠ small sample
  LOW                 50    35   70.0%
  MEDIUM             150   121   80.7%
  NO-CONFIDENCE        1     1  100.0%  ⚠ small sample

## Success by Season Phase

  early           20    16   80.0%
  mid            109    90   82.6%
  late            90    66   73.3%

## Success by Odds Bucket

  heavy_fav (<=1.5)               35    27   77.1%
  medium_fav (2.0-2.5)            83    55   66.3%
  no_clear_fav (>2.5)             17    15   88.2%  ⚠ small sample
  strong_fav (1.5-2.0)            84    75   89.3%

## AVOID Diagnostic

  Total AVOID calls  : 26
  Correctly avoided  : 23 / 26  (88.5%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 4/6
  Under 3.5 hit  : 5/6
  Type OR success: 5/6  (83.3%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Salernitana v Napoli                 BTTS_OVER        OVER_25                A        2g
  Verona v Monza                       UNDER            UNDER_35               A        4g
  Inter v Frosinone                    BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Salernitana v Lazio                  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Torino v Atalanta                    DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Bologna v Roma                       BTTS_OVER        BTTS                   H        2g
  Bologna v Atalanta                   BTTS_OVER        BTTS                   H        1g
  Verona v Cagliari                    BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Roma v Napoli                        AVOID            AVOID_VOLATILE         H        2g
  Atalanta v Lecce                     BTTS_OVER        BTTS                   H        1g
  Cagliari v Empoli                    BTTS_OVER        BTTS                   D        0g
  Milan v Sassuolo                     BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Verona v Salernitana                 BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Sassuolo v Fiorentina                DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        1g
  Torino v Napoli                      DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Atalanta v Udinese                   BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Monza v Sassuolo                     BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Lecce v Fiorentina                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        5g
  Milan v Napoli                       BTTS_OVER        OVER_25                H        1g
  Lazio v Bologna                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Bologna v Lazio                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Atalanta v Inter                     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  Fiorentina v Juventus                AVOID            AVOID_VOLATILE         A        1g
  Frosinone v Empoli                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Torino v Sassuolo                    AVOID            AVOID_VOLATILE         H        3g
  Sassuolo v Salernitana               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Genoa v Verona                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Lecce v Milan                        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        4g
  Monza v Torino                       AVOID            AVOID_VOLATILE         D        2g
  Lazio v Roma                         AVOID            AVOID_VOLATILE         D        0g
  Napoli v Empoli                      DIRECTION        DIRECTION_AWAY         A        1g
  Fiorentina v Bologna                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Udinese v Atalanta                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        2g
  Milan v Fiorentina                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Cagliari v Monza                     AVOID            AVOID_VOLATILE         D        2g
  Empoli v Sassuolo                    AVOID            AVOID_VOLATILE         A        7g
  Roma v Udinese                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Juventus v Inter                     AVOID            AVOID_VOLATILE         D        2g
  Bologna v Torino                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Verona v Lecce                       AVOID            AVOID_VOLATILE         D        4g

## Sample Size Warnings

  ⚠ DIRECTION: only 7 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 6 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 4 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 2 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
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