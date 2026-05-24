# Season Replay Audit — Eredivisie 2023

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 63
- Predictions with OK model : 205
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 205
- Evaluatable (type): 175
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     23    19   82.6%  
  BTTS_OVER                115    85   73.9%  over25=76/115  btts=63/115
  DIRECTION                  3     2   66.7%    ⚠ n<20
  DOUBLE_CHANCE             32    25   78.1%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                      2     2  100.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            48    25   52.1%  BTTS_OVER
  BTTS                        29    16   55.2%  BTTS_OVER
  DIRECTION_AWAY               1     1  100.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               1     1  100.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            23    18   78.3%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2             9     7   77.8%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     38    25   65.8%  BTTS_OVER
  UNDER_35                     2     2  100.0%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 85/115  (73.9%)
  Subtype BOTH_OVER25_BTTS      : 25/48  (52.1%)
  Subtype BTTS                  : 16/29  (55.2%)
  Subtype OVER_25               : 25/38  (65.8%)

### Best Performing Subtypes
  DIRECTION_AWAY           100.0%  (1/1)
  DIRECTION_HOME           100.0%  (1/1)
  UNDER_35                 100.0%  (2/2)
  DOUBLE_CHANCE_1X         78.3%  (18/23)
  DOUBLE_CHANCE_X2         77.8%  (7/9)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         52.1%  (25/48)
  BTTS                     55.2%  (16/29)
  OVER_25                  65.8%  (25/38)
  DOUBLE_CHANCE_X2         77.8%  (7/9)
  DOUBLE_CHANCE_1X         78.3%  (18/23)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             38    29   76.3%
  low (3-5)               47    36   76.6%
  medium (5-7)            90    68   75.6%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              3     1   33.3%  ⚠ small sample
  low (<4)                45    37   82.2%
  medium (4-6)           127    95   74.8%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                34    26   76.5%
  LOW                 35    27   77.1%
  MEDIUM             104    78   75.0%
  NO-CONFIDENCE        2     2  100.0%  ⚠ small sample

## Success by Season Phase

  mid             92    65   70.7%
  late            83    68   81.9%

## Success by Odds Bucket

  heavy_fav (<=1.5)               53    41   77.4%
  medium_fav (2.0-2.5)            46    38   82.6%
  no_clear_fav (>2.5)              7     5   71.4%  ⚠ small sample
  strong_fav (1.5-2.0)            69    49   71.0%

## AVOID Diagnostic

  Total AVOID calls  : 23
  Correctly avoided  : 19 / 23  (82.6%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 2/2
  Under 3.5 hit  : 2/2
  Type OR success: 2/2  (100.0%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Feyenoord v AZ Alkmaar               BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Zwolle v Waalwijk                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Sparta Rotterdam v Utrecht           DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Feyenoord v PSV Eindhoven            AVOID            AVOID_VOLATILE         A        3g
  PSV Eindhoven v Heerenveen           BTTS_OVER        OVER_25                H        2g
  Go Ahead Eagles v Utrecht            AVOID            AVOID_VOLATILE         A        2g
  For Sittard v Waalwijk               BTTS_OVER        OVER_25                H        1g
  Vitesse v Heracles                   BTTS_OVER        OVER_25                H        2g
  For Sittard v Sparta Rotterdam       AVOID            AVOID_VOLATILE         A        2g
  Volendam v Almere City               BTTS_OVER        OVER_25                A        1g
  Nijmegen v Twente                    BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Sparta Rotterdam v Go Ahead Eagles   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Zwolle v Vitesse                     BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  PSV Eindhoven v Almere City          BTTS_OVER        OVER_25                H        2g
  Feyenoord v Twente                   BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  AZ Alkmaar v Feyenoord               BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Sparta Rotterdam v Zwolle            BTTS_OVER        BTTS                   A        2g
  Waalwijk v Nijmegen                  BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Almere City v AZ Alkmaar             BTTS_OVER        OVER_25                D        0g
  Feyenoord v Sparta Rotterdam         BTTS_OVER        BTTS                   H        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Volendam v Sparta Rotterdam          AVOID            AVOID_VOLATILE         A        5g
  PSV Eindhoven v Zwolle               BTTS_OVER        OVER_25                H        4g
  Almere City v Ajax                   BTTS_OVER        BOTH_OVER25_BTTS       D        4g
  Excelsior v Feyenoord                BTTS_OVER        BOTH_OVER25_BTTS       A        6g
  Heerenveen v For Sittard             AVOID            AVOID_VOLATILE         H        3g
  Twente v PSV Eindhoven               BTTS_OVER        OVER_25                A        3g
  Ajax v Vitesse                       BTTS_OVER        OVER_25                H        5g
  Nijmegen v Go Ahead Eagles           BTTS_OVER        OVER_25                D        2g
  Almere City v Heracles               BTTS_OVER        BOTH_OVER25_BTTS       A        5g
  Heerenveen v Almere City             BTTS_OVER        OVER_25                H        3g
  Volendam v Zwolle                    AVOID            AVOID_VOLATILE         A        5g
  For Sittard v Vitesse                DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Waalwijk v Excelsior                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Heracles v Sparta Rotterdam          AVOID            AVOID_VOLATILE         A        1g
  Go Ahead Eagles v Twente             DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        4g
  Nijmegen v Ajax                      BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Utrecht v AZ Alkmaar                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       D        2g
  AZ Alkmaar v Nijmegen                BTTS_OVER        BTTS                   A        3g
  Waalwijk v Ajax                      BTTS_OVER        OVER_25                A        5g
  Feyenoord v Volendam                 BTTS_OVER        BOTH_OVER25_BTTS       H        4g

## Sample Size Warnings

  ⚠ DIRECTION: only 3 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 2 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 1 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 1 evaluatable matches.
  ⚠ subtype DOUBLE_CHANCE_X2: only 9 evaluatable matches.
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