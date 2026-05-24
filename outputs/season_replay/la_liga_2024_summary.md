# Season Replay Audit — La Liga 2024

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 103
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
  AVOID                     24    17   70.8%  
  BTTS_OVER                139    91   65.5%  over25=72/139  btts=77/139
  DIRECTION                  5     5  100.0%    ⚠ n<20
  DOUBLE_CHANCE             64    49   76.6%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                     11    11  100.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            27    13   48.1%  BTTS_OVER
  BTTS                        99    50   50.5%  BTTS_OVER
  DIRECTION_AWAY               1     1  100.0%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               4     4  100.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            45    36   80.0%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            19    13   68.4%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     13    11   84.6%  BTTS_OVER  ⚠ n<20
  UNDER_35                    11    11  100.0%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 91/139  (65.5%)
  Subtype BOTH_OVER25_BTTS      : 13/27  (48.1%)
  Subtype BTTS                  : 50/99  (50.5%)
  Subtype OVER_25               : 11/13  (84.6%)

### Best Performing Subtypes
  DIRECTION_AWAY           100.0%  (1/1)
  DIRECTION_HOME           100.0%  (4/4)
  UNDER_35                 100.0%  (11/11)
  OVER_25                  84.6%  (11/13)
  DOUBLE_CHANCE_1X         80.0%  (36/45)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         48.1%  (13/27)
  BTTS                     50.5%  (50/99)
  DOUBLE_CHANCE_X2         68.4%  (13/19)
  DOUBLE_CHANCE_1X         80.0%  (36/45)
  OVER_25                  84.6%  (11/13)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             29    21   72.4%
  low (3-5)               93    60   64.5%
  medium (5-7)           120    92   76.7%
  very_low (<3)            1     0    0.0%  ⚠ small sample

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               103    83   80.6%
  medium (4-6)           140    90   64.3%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                26    18   69.2%
  LOW                 45    30   66.7%
  MEDIUM             169   122   72.2%
  NO-CONFIDENCE        3     3  100.0%  ⚠ small sample

## Success by Season Phase

  early           23    14   60.9%
  mid            107    82   76.6%
  late           113    77   68.1%

## Success by Odds Bucket

  heavy_fav (<=1.5)               48    37   77.1%
  medium_fav (2.0-2.5)            68    46   67.6%
  no_clear_fav (>2.5)             23    13   56.5%
  strong_fav (1.5-2.0)           104    77   74.0%

## AVOID Diagnostic

  Total AVOID calls  : 24
  Correctly avoided  : 17 / 24  (70.8%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 7/11
  Under 3.5 hit  : 11/11
  Type OR success: 11/11  (100.0%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Espanol v Sevilla                    BTTS_OVER        BTTS                   A        2g
  Las Palmas v Girona                  BTTS_OVER        BTTS                   H        1g
  Betis v Ath Madrid                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        1g
  Sociedad v Osasuna                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Mallorca v Ath Bilbao                BTTS_OVER        BTTS                   D        0g
  Osasuna v Valladolid                 BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Celta v Getafe                       BTTS_OVER        BTTS                   H        1g
  Getafe v Girona                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Sociedad v Barcelona                 DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        1g
  Getafe v Valladolid                  BTTS_OVER        BTTS                   H        2g
  Valencia v Betis                     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        6g
  Celta v Mallorca                     BTTS_OVER        BTTS                   H        2g
  Ath Bilbao v Villarreal              BTTS_OVER        BOTH_OVER25_BTTS       H        2g
  Getafe v Espanol                     BTTS_OVER        BTTS                   H        1g
  Espanol v Osasuna                    BTTS_OVER        BTTS                   D        0g
  Barcelona v Leganes                  BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Las Palmas v Espanol                 BTTS_OVER        BTTS                   H        1g
  Vallecano v Celta                    DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Alaves v Girona                      BTTS_OVER        OVER_25                A        1g
  Valladolid v Betis                   BTTS_OVER        BTTS                   H        1g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Real Madrid v Barcelona              AVOID            AVOID_VOLATILE         A        4g
  Valladolid v Villarreal              BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Vallecano v Alaves                   AVOID            AVOID_VOLATILE         H        1g
  Leganes v Celta                      BTTS_OVER        BTTS                   H        3g
  Getafe v Valencia                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Alaves v Mallorca                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Girona v Leganes                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        7g
  Barcelona v Espanol                  BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  Ath Bilbao v Betis                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Sevilla v Sociedad                   UNDER            UNDER_35               A        2g
  Vallecano v Las Palmas               BTTS_OVER        BTTS                   A        4g
  Villarreal v Alaves                  BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Valladolid v Ath Bilbao              BTTS_OVER        BTTS                   D        2g
  Betis v Celta                        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Mallorca v Ath Madrid                DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        1g
  Ath Madrid v Alaves                  DIRECTION        DIRECTION_HOME         H        3g
  Girona v Espanol                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        5g
  Las Palmas v Mallorca                AVOID            AVOID_VOLATILE         A        5g
  Celta v Barcelona                    BTTS_OVER        OVER_25                D        4g
  Osasuna v Villarreal                 BTTS_OVER        BOTH_OVER25_BTTS       D        4g

## Sample Size Warnings

  ⚠ DIRECTION: only 5 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 11 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 1 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 4 evaluatable matches.
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