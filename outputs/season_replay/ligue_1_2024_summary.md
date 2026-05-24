# Season Replay Audit — Ligue 1 2024

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
- Evaluatable (type): 192
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     20    12   60.0%  
  BTTS_OVER                105    76   72.4%  over25=65/105  btts=70/105
  DIRECTION                 28    18   64.3%  
  DOUBLE_CHANCE             34    19   55.9%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      5     5  100.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            45    26   57.8%  BTTS_OVER
  BTTS                        48    31   64.6%  BTTS_OVER
  DIRECTION_AWAY               2     1   50.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME              24    17   70.8%  DIRECTION
  DOUBLE_CHANCE_1X            15     6   40.0%  DOUBLE_CHANCE  ⚠ n<20
  DOUBLE_CHANCE_X2            19    13   68.4%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     12     5   41.7%  BTTS_OVER  ⚠ n<20
  UNDER_35                     5     5  100.0%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 76/105  (72.4%)
  Subtype BOTH_OVER25_BTTS      : 26/45  (57.8%)
  Subtype BTTS                  : 31/48  (64.6%)
  Subtype OVER_25               : 5/12  (41.7%)

### Best Performing Subtypes
  UNDER_35                 100.0%  (5/5)
  DIRECTION_HOME           70.8%  (17/24)
  DOUBLE_CHANCE_X2         68.4%  (13/19)
  BTTS                     64.6%  (31/48)
  BOTH_OVER25_BTTS         57.8%  (26/45)

### Worst Performing Subtypes
  DOUBLE_CHANCE_1X         40.0%  (6/15)
  OVER_25                  41.7%  (5/12)
  DIRECTION_AWAY           50.0%  (1/2)
  BOTH_OVER25_BTTS         57.8%  (26/45)
  BTTS                     64.6%  (31/48)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             25    20   80.0%
  low (3-5)               59    36   61.0%
  medium (5-7)           108    74   68.5%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)                79    50   63.3%
  medium (4-6)           113    80   70.8%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                24    19   79.2%
  LOW                 25    18   72.0%
  MEDIUM             142    93   65.5%
  NO-CONFIDENCE        1     0    0.0%  ⚠ small sample

## Success by Season Phase

  mid             93    60   64.5%
  late            99    70   70.7%

## Success by Odds Bucket

  heavy_fav (<=1.5)               45    36   80.0%
  medium_fav (2.0-2.5)            56    35   62.5%
  no_clear_fav (>2.5)              7     5   71.4%  ⚠ small sample
  strong_fav (1.5-2.0)            84    54   64.3%

## AVOID Diagnostic

  Total AVOID calls  : 20
  Correctly avoided  : 12 / 20  (60.0%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 3/5
  Under 3.5 hit  : 5/5
  Type OR success: 5/5  (100.0%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  St Etienne v Montpellier             BTTS_OVER        OVER_25                H        1g
  Nantes v Le Havre                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Auxerre v Angers                     BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Reims v Lens                         BTTS_OVER        BTTS                   A        2g
  Toulouse v Auxerre                   BTTS_OVER        OVER_25                H        2g
  Le Havre v Angers                    AVOID            AVOID_VOLATILE         A        1g
  Auxerre v Paris SG                   BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Monaco v Toulouse                    BTTS_OVER        OVER_25                H        2g
  Nantes v Rennes                      AVOID            AVOID_VOLATILE         H        1g
  Reims v Monaco                       BTTS_OVER        BTTS                   D        0g
  Rennes v Angers                      DIRECTION        NONE                   H        2g
  St Etienne v Reims                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        4g
  Lyon v Montpellier                   BTTS_OVER        OVER_25                H        1g
  Lens v Toulouse                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Angers v Brest                       AVOID            AVOID_VOLATILE         H        2g
  Auxerre v Lille                      BTTS_OVER        BTTS                   D        0g
  Brest v Lyon                         AVOID            AVOID_VOLATILE         H        3g
  Montpellier v Angers                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        4g
  Rennes v Brest                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Reims v Le Havre                     DIRECTION        DIRECTION_HOME         D        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Reims v Lyon                         BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Nice v Strasbourg                    BTTS_OVER        BTTS                   H        3g
  Rennes v St Etienne                  DIRECTION        DIRECTION_HOME         H        5g
  Brest v Strasbourg                   BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  Paris SG v Nantes                    BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Marseille v Monaco                   BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Montpellier v Lille                  BTTS_OVER        OVER_25                D        4g
  Lyon v Nice                          BTTS_OVER        BTTS                   H        5g
  Nice v Le Havre                      DIRECTION        DIRECTION_HOME         H        3g
  Angers v Lyon                        BTTS_OVER        BTTS                   A        3g
  Lens v Montpellier                   DIRECTION        DIRECTION_HOME         H        2g
  Strasbourg v Reims                   AVOID            AVOID_VOLATILE         D        0g
  St Etienne v Marseille               DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        2g
  Toulouse v St Etienne                DIRECTION        DIRECTION_HOME         H        3g
  Marseille v Lille                    BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Auxerre v Lens                       DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        4g
  Paris SG v Lyon                      BTTS_OVER        BTTS                   H        4g
  Montpellier v Nice                   BTTS_OVER        BOTH_OVER25_BTTS       D        4g
  Brest v Nantes                       BTTS_OVER        BTTS                   H        5g
  Monaco v Paris SG                    BTTS_OVER        BTTS                   A        6g

## Sample Size Warnings

  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 5 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 2 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype UNDER_35: only 5 evaluatable matches.

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