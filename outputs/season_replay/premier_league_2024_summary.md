# Season Replay Audit — Premier League 2024

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 83
- Predictions with OK model : 280
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 280
- Evaluatable (type): 247
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     26    19   73.1%  
  BTTS_OVER                160   113   70.6%  over25=97/160  btts=90/160
  DIRECTION                  9     4   44.4%    ⚠ n<20
  DOUBLE_CHANCE             52    42   80.8%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            69    31   44.9%  BTTS_OVER
  BTTS                        58    33   56.9%  BTTS_OVER
  DIRECTION_AWAY               3     1   33.3%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               5     3   60.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            39    31   79.5%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            13    11   84.6%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     33    21   63.6%  BTTS_OVER

### BTTS_OVER Subtype Split

  Type-level OR : 113/160  (70.6%)
  Subtype BOTH_OVER25_BTTS      : 31/69  (44.9%)
  Subtype BTTS                  : 33/58  (56.9%)
  Subtype OVER_25               : 21/33  (63.6%)

### Best Performing Subtypes
  DOUBLE_CHANCE_X2         84.6%  (11/13)
  DOUBLE_CHANCE_1X         79.5%  (31/39)
  OVER_25                  63.6%  (21/33)
  DIRECTION_HOME           60.0%  (3/5)
  BTTS                     56.9%  (33/58)

### Worst Performing Subtypes
  DIRECTION_AWAY           33.3%  (1/3)
  BOTH_OVER25_BTTS         44.9%  (31/69)
  BTTS                     56.9%  (33/58)
  DIRECTION_HOME           60.0%  (3/5)
  OVER_25                  63.6%  (21/33)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             34    24   70.6%
  low (3-5)               78    51   65.4%
  medium (5-7)           135   103   76.3%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)                74    55   74.3%
  medium (4-6)           173   123   71.1%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                32    22   68.8%
  LOW                 45    31   68.9%
  MEDIUM             167   122   73.1%
  NO-CONFIDENCE        3     3  100.0%  ⚠ small sample

## Success by Season Phase

  early           24    18   75.0%
  mid            112    83   74.1%
  late           111    77   69.4%

## Success by Odds Bucket

  heavy_fav (<=1.5)               71    54   76.1%
  medium_fav (2.0-2.5)            67    43   64.2%
  no_clear_fav (>2.5)             10     6   60.0%  ⚠ small sample
  strong_fav (1.5-2.0)            99    75   75.8%

## AVOID Diagnostic

  Total AVOID calls  : 26
  Correctly avoided  : 19 / 26  (73.1%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  West Ham v Everton                   BTTS_OVER        BTTS                   D        0g
  Wolves v Southampton                 BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Liverpool v Aston Villa              BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Everton v Brentford                  BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Newcastle v West Ham                 BTTS_OVER        BTTS                   A        2g
  Nott'm Forest v Ipswich              BTTS_OVER        BTTS                   H        1g
  Liverpool v Man City                 BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Bournemouth v Tottenham              AVOID            AVOID_VOLATILE         H        1g
  Man United v Nott'm Forest           DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        5g
  Aston Villa v Southampton            BTTS_OVER        BTTS                   H        1g
  Brentford v Nott'm Forest            AVOID            AVOID_VOLATILE         A        2g
  Fulham v Southampton                 BTTS_OVER        BTTS                   D        0g
  Bournemouth v Crystal Palace         BTTS_OVER        BTTS                   D        0g
  Wolves v Man United                  BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Brighton v Brentford                 BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Leicester v Man City                 BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Everton v Nott'm Forest              DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Ipswich v Chelsea                    BTTS_OVER        BTTS                   H        2g
  Man United v Newcastle               BTTS_OVER        OVER_25                A        2g
  Leicester v Crystal Palace           BTTS_OVER        BOTH_OVER25_BTTS       A        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Brentford v Bournemouth              BTTS_OVER        BOTH_OVER25_BTTS       H        5g
  Crystal Palace v Fulham              AVOID            AVOID_VOLATILE         A        2g
  Brighton v Man City                  BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Chelsea v Arsenal                    AVOID            AVOID_VOLATILE         D        2g
  Tottenham v Ipswich                  BTTS_OVER        BTTS                   A        3g
  Man United v Leicester               BTTS_OVER        BTTS                   H        3g
  Fulham v Wolves                      BTTS_OVER        BOTH_OVER25_BTTS       A        5g
  Leicester v Chelsea                  BTTS_OVER        BTTS                   A        3g
  Arsenal v Nott'm Forest              DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Aston Villa v Crystal Palace         DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Bournemouth v Brighton               BTTS_OVER        BTTS                   A        3g
  Man City v Tottenham                 BTTS_OVER        BOTH_OVER25_BTTS       A        4g
  Ipswich v Man United                 BTTS_OVER        BTTS                   D        2g
  Southampton v Liverpool              DIRECTION        DIRECTION_AWAY         A        5g
  Brighton v Southampton               BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Brentford v Leicester                BTTS_OVER        BOTH_OVER25_BTTS       H        5g
  Wolves v Bournemouth                 BTTS_OVER        BOTH_OVER25_BTTS       A        6g
  West Ham v Arsenal                   BTTS_OVER        BTTS                   A        7g
  Tottenham v Fulham                   BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Chelsea v Aston Villa                BTTS_OVER        BTTS                   H        3g

## Sample Size Warnings

  ⚠ DIRECTION: only 9 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 3 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 5 evaluatable matches.
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