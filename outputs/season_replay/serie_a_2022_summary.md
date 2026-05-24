# Season Replay Audit — Serie A 2022

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 94
- Predictions with OK model : 280
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 280
- Evaluatable (type): 240
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     35    28   80.0%  
  BTTS_OVER                 56    32   57.1%  over25=27/56  btts=28/56
  DIRECTION                 16    10   62.5%    ⚠ n<20
  DOUBLE_CHANCE            118    92   78.0%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                     15    11   73.3%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            15     7   46.7%  BTTS_OVER  ⚠ n<20
  BTTS                        38    20   52.6%  BTTS_OVER
  DIRECTION_AWAY               7     6   85.7%  DIRECTION  ⚠ n<20
  DIRECTION_HOME               9     4   44.4%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            74    58   78.4%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            44    34   77.3%  DOUBLE_CHANCE
  OVER_25                      3     2   66.7%  BTTS_OVER  ⚠ n<20
  UNDER_35                    15    11   73.3%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 32/56  (57.1%)
  Subtype BOTH_OVER25_BTTS      : 7/15  (46.7%)
  Subtype BTTS                  : 20/38  (52.6%)
  Subtype OVER_25               : 2/3  (66.7%)

### Best Performing Subtypes
  DIRECTION_AWAY           85.7%  (6/7)
  DOUBLE_CHANCE_1X         78.4%  (58/74)
  DOUBLE_CHANCE_X2         77.3%  (34/44)
  UNDER_35                 73.3%  (11/15)
  OVER_25                  66.7%  (2/3)

### Worst Performing Subtypes
  DIRECTION_HOME           44.4%  (4/9)
  BOTH_OVER25_BTTS         46.7%  (7/15)
  BTTS                     52.6%  (20/38)
  OVER_25                  66.7%  (2/3)
  UNDER_35                 73.3%  (11/15)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             25    15   60.0%
  low (3-5)               90    65   72.2%
  medium (5-7)           125    93   74.4%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               168   128   76.2%
  medium (4-6)            72    45   62.5%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                24    14   58.3%
  LOW                 57    40   70.2%
  MEDIUM             153   114   74.5%
  NO-CONFIDENCE        6     5   83.3%  ⚠ small sample

## Success by Season Phase

  early           18    12   66.7%  ⚠ small sample
  mid            112    80   71.4%
  late           110    81   73.6%

## Success by Odds Bucket

  heavy_fav (<=1.5)               42    33   78.6%
  medium_fav (2.0-2.5)            74    52   70.3%
  no_clear_fav (>2.5)             16    12   75.0%  ⚠ small sample
  strong_fav (1.5-2.0)           108    76   70.4%

## AVOID Diagnostic

  Total AVOID calls  : 35
  Correctly avoided  : 28 / 35  (80.0%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 8/15
  Under 3.5 hit  : 11/15
  Type OR success: 11/15  (73.3%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Atalanta v Lazio                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        2g
  Cremonese v Sampdoria                AVOID            AVOID_VOLATILE         A        1g
  Lazio v Salernitana                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        4g
  Cremonese v Udinese                  BTTS_OVER        BTTS                   D        0g
  Monza v Bologna                      AVOID            AVOID_VOLATILE         A        3g
  Juventus v Inter                     AVOID            AVOID_VOLATILE         H        2g
  Roma v Lazio                         AVOID            AVOID_VOLATILE         A        1g
  Cremonese v Milan                    BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Napoli v Empoli                      BTTS_OVER        BTTS                   H        2g
  Sampdoria v Lecce                    AVOID            AVOID_VOLATILE         A        2g
  Roma v Bologna                       BTTS_OVER        BTTS                   H        1g
  Lecce v Lazio                        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Sassuolo v Sampdoria                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Spezia v Lecce                       BTTS_OVER        BTTS                   D        0g
  Inter v Verona                       BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Roma v Fiorentina                    BTTS_OVER        BTTS                   H        2g
  Torino v Spezia                      BTTS_OVER        BTTS                   A        1g
  Sassuolo v Lazio                     BTTS_OVER        OVER_25                A        2g
  Salernitana v Napoli                 BTTS_OVER        BOTH_OVER25_BTTS       A        2g
  Fiorentina v Torino                  BTTS_OVER        BTTS                   A        1g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Juventus v Empoli                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        4g
  Bologna v Lecce                      AVOID            AVOID_VOLATILE         H        2g
  Lecce v Juventus                     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        1g
  Inter v Sampdoria                    BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Empoli v Atalanta                    DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        2g
  Spezia v Fiorentina                  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  Torino v Milan                       BTTS_OVER        BTTS                   H        3g
  Verona v Roma                        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        4g
  Udinese v Lecce                      BTTS_OVER        BTTS                   D        2g
  Salernitana v Cremonese              BTTS_OVER        BTTS                   D        4g
  Atalanta v Napoli                    DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        3g
  Milan v Spezia                       BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Bologna v Torino                     BTTS_OVER        BTTS                   H        3g
  Monza v Verona                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Sampdoria v Fiorentina               DOUBLE_CHANCE    DOUBLE_CHANCE_X2       A        2g
  Lecce v Atalanta                     BTTS_OVER        BTTS                   H        3g
  Fiorentina v Salernitana             BTTS_OVER        BTTS                   H        3g
  Inter v Bologna                      BTTS_OVER        BOTH_OVER25_BTTS       H        7g
  Torino v Sampdoria                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Lazio v Monza                        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g

## Sample Size Warnings

  ⚠ DIRECTION: only 16 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 15 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_AWAY: only 7 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 9 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype OVER_25: only 3 evaluatable matches.

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