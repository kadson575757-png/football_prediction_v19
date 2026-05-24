# Season Replay Audit — Premier League 2023

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 89
- Predictions with OK model : 280
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 280
- Evaluatable (type): 263
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     33    30   90.9%  
  BTTS_OVER                200   150   75.0%  over25=130/200  btts=126/200
  DIRECTION                  2     2  100.0%    ⚠ n<20
  DOUBLE_CHANCE             28    21   75.0%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS           115    64   55.7%  BTTS_OVER
  BTTS                        46    32   69.6%  BTTS_OVER
  DIRECTION_AWAY               1     1  100.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               1     1  100.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            18    14   77.8%  DOUBLE_CHANCE  ⚠ n<20
  DOUBLE_CHANCE_X2            10     7   70.0%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     39    20   51.3%  BTTS_OVER

### BTTS_OVER Subtype Split

  Type-level OR : 150/200  (75.0%)
  Subtype BOTH_OVER25_BTTS      : 64/115  (55.7%)
  Subtype BTTS                  : 32/46  (69.6%)
  Subtype OVER_25               : 20/39  (51.3%)

### Best Performing Subtypes
  DIRECTION_AWAY           100.0%  (1/1)
  DIRECTION_HOME           100.0%  (1/1)
  DOUBLE_CHANCE_1X         77.8%  (14/18)
  DOUBLE_CHANCE_X2         70.0%  (7/10)
  BTTS                     69.6%  (32/46)

### Worst Performing Subtypes
  OVER_25                  51.3%  (20/39)
  BOTH_OVER25_BTTS         55.7%  (64/115)
  BTTS                     69.6%  (32/46)
  DOUBLE_CHANCE_X2         70.0%  (7/10)
  DOUBLE_CHANCE_1X         77.8%  (14/18)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             50    32   64.0%
  low (3-5)               87    69   79.3%
  medium (5-7)           126   102   81.0%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (6-10)              4     2   50.0%  ⚠ small sample
  low (<4)                36    27   75.0%
  medium (4-6)           223   174   78.0%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                39    26   66.7%
  LOW                 55    38   69.1%
  MEDIUM             165   135   81.8%
  NO-CONFIDENCE        4     4  100.0%  ⚠ small sample

## Success by Season Phase

  early           23    16   69.6%
  mid            118    94   79.7%
  late           122    93   76.2%

## Success by Odds Bucket

  heavy_fav (<=1.5)               71    51   71.8%
  medium_fav (2.0-2.5)            81    63   77.8%
  no_clear_fav (>2.5)             11     9   81.8%  ⚠ small sample
  strong_fav (1.5-2.0)           100    80   80.0%

## AVOID Diagnostic

  Total AVOID calls  : 33
  Correctly avoided  : 30 / 33  (90.9%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Newcastle v Arsenal                  AVOID            AVOID_VOLATILE         H        1g
  Nott'm Forest v Aston Villa          BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Tottenham v Chelsea                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        5g
  Bournemouth v Newcastle              BTTS_OVER        OVER_25                H        2g
  Man United v Luton                   BTTS_OVER        BTTS                   H        1g
  Crystal Palace v Everton             DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        5g
  Brentford v Arsenal                  BTTS_OVER        OVER_25                A        1g
  Wolves v Burnley                     BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Sheffield United v Liverpool         BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Aston Villa v Man City               BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Man United v Chelsea                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Crystal Palace v Bournemouth         BTTS_OVER        OVER_25                A        2g
  Everton v Newcastle                  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Sheffield United v Brentford         BTTS_OVER        OVER_25                H        1g
  Aston Villa v Arsenal                AVOID            AVOID_VOLATILE         H        1g
  Everton v Chelsea                    BTTS_OVER        OVER_25                H        2g
  Nott'm Forest v Tottenham            BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Chelsea v Sheffield United           BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Arsenal v Brighton                   BTTS_OVER        BTTS                   H        2g
  West Ham v Man United                BTTS_OVER        OVER_25                H        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Fulham v Man United                  AVOID            AVOID_VOLATILE         A        1g
  Brentford v West Ham                 AVOID            AVOID_VOLATILE         H        5g
  Everton v Brighton                   AVOID            AVOID_VOLATILE         D        2g
  Man City v Bournemouth               BTTS_OVER        OVER_25                H        7g
  Sheffield United v Wolves            BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Luton v Liverpool                    BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Wolves v Tottenham                   BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Aston Villa v Fulham                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Brighton v Sheffield United          BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Liverpool v Brentford                BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  West Ham v Nott'm Forest             BTTS_OVER        BOTH_OVER25_BTTS       H        5g
  Sheffield United v Bournemouth       BTTS_OVER        BOTH_OVER25_BTTS       A        4g
  Nott'm Forest v Brighton             BTTS_OVER        BTTS                   A        5g
  Luton v Crystal Palace               BTTS_OVER        BTTS                   H        3g
  Burnley v West Ham                   BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Newcastle v Chelsea                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        5g
  Man City v Liverpool                 BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Tottenham v Aston Villa              BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Everton v Man United                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  Fulham v Wolves                      AVOID            AVOID_VOLATILE         H        5g

## Sample Size Warnings

  ⚠ DIRECTION: only 2 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 1 evaluatable matches.
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