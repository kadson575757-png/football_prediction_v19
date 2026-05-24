# Season Replay Audit — Ligue 1 2023

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
- Predictions with OK model : 206
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 206
- Evaluatable (type): 186
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     25    18   72.0%  
  BTTS_OVER                 63    41   65.1%  over25=34/63  btts=38/63
  DIRECTION                 38    22   57.9%  
  DOUBLE_CHANCE             51    35   68.6%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      9     8   88.9%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            17     8   47.1%  BTTS_OVER  ⚠ n<20
  BTTS                        39    27   69.2%  BTTS_OVER
  DIRECTION_AWAY               1     0    0.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME              35    22   62.9%  DIRECTION
  DOUBLE_CHANCE_1X            28    17   60.7%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            23    18   78.3%  DOUBLE_CHANCE
  OVER_25                      7     3   42.9%  BTTS_OVER  ⚠ n<20
  UNDER_35                     9     8   88.9%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 41/63  (65.1%)
  Subtype BOTH_OVER25_BTTS      : 8/17  (47.1%)
  Subtype BTTS                  : 27/39  (69.2%)
  Subtype OVER_25               : 3/7  (42.9%)

### Best Performing Subtypes
  UNDER_35                 88.9%  (8/9)
  DOUBLE_CHANCE_X2         78.3%  (18/23)
  BTTS                     69.2%  (27/39)
  DIRECTION_HOME           62.9%  (22/35)
  DOUBLE_CHANCE_1X         60.7%  (17/28)

### Worst Performing Subtypes
  DIRECTION_AWAY           0.0%  (0/1)
  OVER_25                  42.9%  (3/7)
  BOTH_OVER25_BTTS         47.1%  (8/17)
  DOUBLE_CHANCE_1X         60.7%  (17/28)
  DIRECTION_HOME           62.9%  (22/35)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             13    10   76.9%  ⚠ small sample
  low (3-5)               68    48   70.6%
  medium (5-7)           105    66   62.9%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               115    79   68.7%
  medium (4-6)            71    45   63.4%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                10     9   90.0%  ⚠ small sample
  LOW                 44    31   70.5%
  MEDIUM             128    80   62.5%
  NO-CONFIDENCE        4     4  100.0%  ⚠ small sample

## Success by Season Phase

  early            1     0    0.0%  ⚠ small sample
  mid             92    64   69.6%
  late            93    60   64.5%

## Success by Odds Bucket

  heavy_fav (<=1.5)               33    27   81.8%
  medium_fav (2.0-2.5)            57    38   66.7%
  no_clear_fav (>2.5)             17    10   58.8%  ⚠ small sample
  strong_fav (1.5-2.0)            79    49   62.0%

## AVOID Diagnostic

  Total AVOID calls  : 25
  Correctly avoided  : 18 / 25  (72.0%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 7/9
  Under 3.5 hit  : 8/9
  Type OR success: 8/9  (88.9%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Lille v Toulouse                     DIRECTION        DIRECTION_HOME         D        2g
  Metz v Nantes                        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        4g
  Rennes v Lyon                        BTTS_OVER        BTTS                   A        1g
  Clermont v Lens                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Montpellier v Brest                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        4g
  Le Havre v Paris SG                  BTTS_OVER        OVER_25                A        2g
  Brest v Strasbourg                   DIRECTION        DIRECTION_HOME         D        2g
  Monaco v Lyon                        DIRECTION        DIRECTION_HOME         A        1g
  Le Havre v Nice                      UNDER            UNDER_35               H        4g
  Toulouse v Rennes                    BTTS_OVER        BTTS                   D        0g
  Lorient v Strasbourg                 AVOID            AVOID_VOLATILE         A        3g
  Nantes v Brest                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Reims v Le Havre                     DIRECTION        NONE                   H        1g
  Strasbourg v Lille                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Monaco v Reims                       DIRECTION        DIRECTION_HOME         A        4g
  Le Havre v Lyon                      DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        4g
  Nantes v Clermont                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Brest v Montpellier                  DIRECTION        DIRECTION_AWAY         H        2g
  Paris SG v Brest                     DIRECTION        DIRECTION_HOME         D        4g
  Toulouse v Lens                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Lens v Marseille                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Paris SG v Monaco                    BTTS_OVER        OVER_25                H        7g
  Strasbourg v Marseille               DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        2g
  Rennes v Reims                       BTTS_OVER        BTTS                   H        4g
  Lyon v Lille                         DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        2g
  Nice v Toulouse                      UNDER            UNDER_35               H        1g
  Montpellier v Clermont               DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Reims v Strasbourg                   DIRECTION        DIRECTION_HOME         H        3g
  Lens v Lyon                          DIRECTION        DIRECTION_HOME         H        5g
  Nantes v Nice                        UNDER            UNDER_35               H        1g
  Brest v Clermont                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Monaco v Montpellier                 DIRECTION        DIRECTION_HOME         H        2g
  Lille v Metz                         DIRECTION        DIRECTION_HOME         H        2g
  Marseille v Rennes                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Marseille v Lyon                     DIRECTION        DIRECTION_HOME         H        3g
  Montpellier v Lens                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        0g
  Paris SG v Nantes                    BTTS_OVER        OVER_25                H        3g
  Rennes v Monaco                      AVOID            AVOID_VOLATILE         A        3g
  Nice v Reims                         DIRECTION        DIRECTION_HOME         H        3g
  Clermont v Lille                     UNDER            UNDER_35               D        0g

## Sample Size Warnings

  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 9 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 1 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype OVER_25: only 7 evaluatable matches.
  ⚠ subtype UNDER_35: only 9 evaluatable matches.

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