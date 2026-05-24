# Season Replay Audit — Serie A 2024

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 102
- Predictions with OK model : 278
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 278
- Evaluatable (type): 232
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     34    31   91.2%  
  BTTS_OVER                 89    53   59.6%  over25=44/89  btts=42/89
  DIRECTION                  6     5   83.3%    ⚠ n<20
  DOUBLE_CHANCE             90    70   77.8%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20
  UNDER                     13     8   61.5%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            18     8   44.4%  BTTS_OVER  ⚠ n<20
  BTTS                        63    30   47.6%  BTTS_OVER
  DIRECTION_HOME               5     4   80.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            62    47   75.8%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            28    23   82.1%  DOUBLE_CHANCE
  OVER_25                      8     5   62.5%  BTTS_OVER  ⚠ n<20
  UNDER_35                    13     8   61.5%  UNDER  ⚠ n<20

### BTTS_OVER Subtype Split

  Type-level OR : 53/89  (59.6%)
  Subtype BOTH_OVER25_BTTS      : 8/18  (44.4%)
  Subtype BTTS                  : 30/63  (47.6%)
  Subtype OVER_25               : 5/8  (62.5%)

### Best Performing Subtypes
  DOUBLE_CHANCE_X2         82.1%  (23/28)
  DIRECTION_HOME           80.0%  (4/5)
  DOUBLE_CHANCE_1X         75.8%  (47/62)
  OVER_25                  62.5%  (5/8)
  UNDER_35                 61.5%  (8/13)

### Worst Performing Subtypes
  BOTH_OVER25_BTTS         44.4%  (8/18)
  BTTS                     47.6%  (30/63)
  UNDER_35                 61.5%  (8/13)
  OVER_25                  62.5%  (5/8)
  DOUBLE_CHANCE_1X         75.8%  (47/62)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             25    15   60.0%
  low (3-5)               84    64   76.2%
  medium (5-7)           123    88   71.5%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)               124    96   77.4%
  medium (4-6)           108    71   65.7%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                21    13   61.9%
  LOW                 54    41   75.9%
  MEDIUM             154   110   71.4%
  NO-CONFIDENCE        3     3  100.0%  ⚠ small sample

## Success by Season Phase

  early           22    17   77.3%
  mid            103    73   70.9%
  late           107    77   72.0%

## Success by Odds Bucket

  heavy_fav (<=1.5)               38    28   73.7%
  medium_fav (2.0-2.5)            68    52   76.5%
  no_clear_fav (>2.5)             18    15   83.3%  ⚠ small sample
  strong_fav (1.5-2.0)           108    72   66.7%

## AVOID Diagnostic

  Total AVOID calls  : 34
  Correctly avoided  : 31 / 34  (91.2%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## UNDER Stability Check

  Under 2.5 hit  : 7/13
  Under 3.5 hit  : 8/13
  Type OR success: 8/13  (61.5%)

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Inter v Venezia                      BTTS_OVER        OVER_25                H        1g
  Napoli v Atalanta                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Parma v Genoa                        BTTS_OVER        BTTS                   A        1g
  Monza v Lazio                        BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Como v Fiorentina                    BTTS_OVER        BTTS                   A        2g
  Venezia v Lecce                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Cagliari v Verona                    BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Roma v Atalanta                      BTTS_OVER        BTTS                   A        2g
  Napoli v Lazio                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        1g
  Monza v Udinese                      DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Empoli v Torino                      AVOID            AVOID_VOLATILE         A        1g
  Cagliari v Atalanta                  BTTS_OVER        BTTS                   A        1g
  Udinese v Napoli                     UNDER            UNDER_35               A        4g
  Como v Roma                          BTTS_OVER        BTTS                   H        2g
  Verona v Milan                       BTTS_OVER        OVER_25                A        1g
  Lecce v Lazio                        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        3g
  Empoli v Lecce                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A        4g
  Udinese v Atalanta                   BTTS_OVER        BTTS                   D        0g
  Monza v Fiorentina                   DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        3g
  Juventus v Milan                     BTTS_OVER        BTTS                   H        2g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  Verona v Roma                        BTTS_OVER        OVER_25                H        5g
  Torino v Fiorentina                  AVOID            AVOID_VOLATILE         A        1g
  Lazio v Cagliari                     BTTS_OVER        BTTS                   H        3g
  Genoa v Como                         AVOID            AVOID_VOLATILE         D        2g
  Lecce v Empoli                       AVOID            AVOID_VOLATILE         D        2g
  Venezia v Parma                      BTTS_OVER        BTTS                   A        3g
  Cagliari v Milan                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        6g
  Juventus v Torino                    DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        2g
  Inter v Napoli                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Roma v Bologna                       BTTS_OVER        BTTS                   A        5g
  Atalanta v Udinese                   DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Fiorentina v Verona                  BTTS_OVER        OVER_25                H        4g
  Verona v Inter                       BTTS_OVER        BOTH_OVER25_BTTS       A        5g
  Parma v Atalanta                     BTTS_OVER        BOTH_OVER25_BTTS       A        4g
  Genoa v Cagliari                     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        4g
  Torino v Monza                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Napoli v Roma                        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        1g
  Lazio v Bologna                      BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  Como v Monza                         BTTS_OVER        BTTS                   D        2g
  Milan v Empoli                       DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g

## Sample Size Warnings

  ⚠ DIRECTION: only 6 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ UNDER: only 13 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
  ⚠ subtype DIRECTION_HOME: only 5 evaluatable matches.
  ⚠ subtype NONE: only 0 evaluatable matches.
  ⚠ subtype OVER_25: only 8 evaluatable matches.

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