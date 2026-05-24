# Season Replay Audit — Ligue 1 2022

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 73
- Predictions with OK model : 280
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 280
- Evaluatable (type): 243
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     24    21   87.5%  
  BTTS_OVER                119    76   63.9%  over25=63/119  btts=62/119
  DIRECTION                 41    25   61.0%  
  DOUBLE_CHANCE             59    43   72.9%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            42    19   45.2%  BTTS_OVER
  BTTS                        65    36   55.4%  BTTS_OVER
  DIRECTION_AWAY               1     1  100.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME              36    24   66.7%  DIRECTION
  DOUBLE_CHANCE_1X            31    21   67.7%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            28    22   78.6%  DOUBLE_CHANCE
  OVER_25                     12     7   58.3%  BTTS_OVER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 76/119  (63.9%)
  Subtype BOTH_OVER25_BTTS      : 19/42  (45.2%)
  Subtype BTTS                  : 36/65  (55.4%)
  Subtype OVER_25               : 7/12  (58.3%)

### Best Performing Subtypes
  DIRECTION_AWAY           100.0%  (1/1)
  DOUBLE_CHANCE_X2         78.6%  (22/28)
  DOUBLE_CHANCE_1X         67.7%  (21/31)
  DIRECTION_HOME           66.7%  (24/36)
  OVER_25                  58.3%  (7/12)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         45.2%  (19/42)
  BTTS                     55.4%  (36/65)
  OVER_25                  58.3%  (7/12)
  DIRECTION_HOME           66.7%  (24/36)
  DOUBLE_CHANCE_1X         67.7%  (21/31)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             26    18   69.2%
  low (3-5)               86    59   68.6%
  medium (5-7)           131    88   67.2%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              1     1  100.0%  ⚠ small sample
  low (<4)               109    74   67.9%
  medium (4-6)           133    90   67.7%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                26    18   69.2%
  LOW                 49    32   65.3%
  MEDIUM             167   114   68.3%
  NO-CONFIDENCE        1     1  100.0%  ⚠ small sample

## Success by Season Phase

  early           25    20   80.0%
  mid            113    74   65.5%
  late           105    71   67.6%

## Success by Odds Bucket

  heavy_fav (<=1.5)               58    38   65.5%
  medium_fav (2.0-2.5)            82    56   68.3%
  no_clear_fav (>2.5)             13     9   69.2%  ⚠ small sample
  strong_fav (1.5-2.0)            90    62   68.9%

## AVOID Diagnostic

  Total AVOID calls  : 24
  Correctly avoided  : 21 / 24  (87.5%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Lorient v Reims                      BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Lens v Montpellier                   BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Marseille v Lens                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Auxerre v Ajaccio                    BTTS_OVER        BTTS                   H        1g
  Monaco v Angers                      BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Lyon v Lille                         BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Reims v Nantes                       BTTS_OVER        BTTS                   H        1g
  Toulouse v Monaco                    BTTS_OVER        BTTS                   A        2g
  Nice v Brest                         BTTS_OVER        BTTS                   H        1g
  Monaco v Marseille                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        5g
  Lille v Angers                       BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Troyes v Nantes                      BTTS_OVER        BTTS                   D        0g
  Auxerre v Monaco                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        5g
  Clermont v Lille                     BTTS_OVER        BTTS                   A        2g
  Lorient v Montpellier                BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Monaco v Brest                       BTTS_OVER        BTTS                   H        1g
  Nantes v Auxerre                     BTTS_OVER        BTTS                   H        1g
  Toulouse v Ajaccio                   BTTS_OVER        BTTS                   H        2g
  Lyon v Clermont                      BTTS_OVER        BTTS                   A        1g
  Lens v Paris SG                      DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        4g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Strasbourg v Lille                   BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Monaco v Clermont                    BTTS_OVER        BTTS                   D        2g
  Troyes v Ajaccio                     AVOID            AVOID_VOLATILE         D        2g
  Rennes v Lyon                        BTTS_OVER        BTTS                   H        5g
  Toulouse v Angers                    BTTS_OVER        BOTH_OVER25_BTTS       H        5g
  Auxerre v Nice                       BTTS_OVER        BTTS                   D        2g
  Paris SG v Marseille                 DIRECTION        DIRECTION_HOME         H        1g
  Nantes v Brest                       AVOID            AVOID_VOLATILE         H        5g
  Ajaccio v Paris SG                   DIRECTION        DIRECTION_AWAY         A        3g
  Montpellier v Lyon                   BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Lille v Monaco                       BTTS_OVER        BOTH_OVER25_BTTS       H        7g
  Nice v Nantes                        BTTS_OVER        BTTS                   D        2g
  Troyes v Lorient                     BTTS_OVER        BOTH_OVER25_BTTS       D        4g
  Angers v Rennes                      BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Reims v Auxerre                      BTTS_OVER        BTTS                   H        3g
  Clermont v Brest                     BTTS_OVER        BTTS                   A        4g
  Toulouse v Strasbourg                AVOID            AVOID_VOLATILE         D        4g
  Lens v Toulouse                      DIRECTION        DIRECTION_HOME         H        3g
  Paris SG v Troyes                    BTTS_OVER        BTTS                   H        7g
  Brest v Reims                        AVOID            AVOID_VOLATILE         D        0g

## Sample Size Warnings

  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 1 evaluatable matches.
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