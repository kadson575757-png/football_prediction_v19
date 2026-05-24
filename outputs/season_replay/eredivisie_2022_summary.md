# Season Replay Audit — Eredivisie 2022

## ✅ TRUE WALK-FORWARD ML MODE

For every matchday group:
- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)
- An ML model was trained on `train_df` features
- Probabilities for the current group came from that model's `predict_proba`
- No pre-trained full-season model was used
- No current or future match results appear in any training fold

### Walk-Forward Training Summary

- ML model used        : logistic_regression
- Distinct cutoff dates: 64
- Predictions with OK model : 204
- Predictions with no model : 0

- Mode              : walk_forward
- Total matches     : 204
- Evaluatable (type): 168
- Data-warning rows : 0

*Diagnostic only. No betting claims.*

## Success Rate by Recommended Market Type

  Type                       n  hits    rate  Notes
  ------------------------------------------------------------
  AVOID                     22    17   77.3%  
  BTTS_OVER                103    70   68.0%  over25=61/103  btts=51/103
  DIRECTION                  2     0    0.0%    ⚠ n<20
  DOUBLE_CHANCE             41    35   85.4%  
  OBSERVE_ONLY               0     0    0.0%    ⚠ n<20

## Success Rate by Recommended Market Subtype

  Subtype                      n  hits    rate  Parent
  -----------------------------------------------------------------
  BOTH_OVER25_BTTS            34    12   35.3%  BTTS_OVER
  BTTS                        42    21   50.0%  BTTS_OVER
  DIRECTION_HOME               1     0    0.0%  DIRECTION  ⚠ n<20
  DOUBLE_CHANCE_1X            28    25   89.3%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2            13    10   76.9%  DOUBLE_CHANCE  ⚠ n<20
  OVER_25                     27    17   63.0%  BTTS_OVER

### BTTS_OVER Subtype Split

  Type-level OR : 70/103  (68.0%)
  Subtype BOTH_OVER25_BTTS      : 12/34  (35.3%)
  Subtype BTTS                  : 21/42  (50.0%)
  Subtype OVER_25               : 17/27  (63.0%)

### Best Performing Subtypes
  DOUBLE_CHANCE_1X         89.3%  (25/28)
  DOUBLE_CHANCE_X2         76.9%  (10/13)
  OVER_25                  63.0%  (17/27)
  BTTS                     50.0%  (21/42)
  BOTH_OVER25_BTTS         35.3%  (12/34)

### Worst Performing Subtypes
  DIRECTION_HOME           0.0%  (0/1)
  BOTH_OVER25_BTTS         35.3%  (12/34)
  BTTS                     50.0%  (21/42)
  OVER_25                  63.0%  (17/27)
  DOUBLE_CHANCE_X2         76.9%  (10/13)

## Success by Control Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  high (7-10)             29    21   72.4%
  low (3-5)               57    38   66.7%
  medium (5-7)            82    63   76.8%

## Success by Chaos Bucket

  Bucket                   n  hits    rate
  ------------------------------------------
  low (<4)                55    45   81.8%
  medium (4-6)           113    77   68.1%

## Success by Confidence

  Confidence           n  hits    rate
  --------------------------------------
  HIGH                28    20   71.4%
  LOW                 38    29   76.3%
  MEDIUM             101    72   71.3%
  NO-CONFIDENCE        1     1  100.0%  ⚠ small sample

## Success by Season Phase

  mid             83    55   66.3%
  late            85    67   78.8%

## Success by Odds Bucket

  heavy_fav (<=1.5)               54    38   70.4%
  medium_fav (2.0-2.5)            50    32   64.0%
  no_clear_fav (>2.5)              9     7   77.8%  ⚠ small sample
  strong_fav (1.5-2.0)            55    45   81.8%

## AVOID Diagnostic

  Total AVOID calls  : 22
  Correctly avoided  : 17 / 22  (77.3%)
  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw).

## Top 20 Misses

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  FC Emmen v Groningen                 BTTS_OVER        BTTS                   D        0g
  For Sittard v FC Emmen               AVOID            AVOID_VOLATILE         A        1g
  Excelsior v Heerenveen               BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Volendam v Feyenoord                 BTTS_OVER        BTTS                   A        2g
  Feyenoord v Cambuur                  DIRECTION        NONE                   H        1g
  PSV Eindhoven v AZ Alkmaar           BTTS_OVER        BOTH_OVER25_BTTS       A        1g
  Waalwijk v Heerenveen                BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  For Sittard v Go Ahead Eagles        BTTS_OVER        BTTS                   A        2g
  PSV Eindhoven v Sparta Rotterdam     BTTS_OVER        OVER_25                D        0g
  Excelsior v Groningen                BTTS_OVER        BOTH_OVER25_BTTS       H        1g
  Heerenveen v AZ Alkmaar              BTTS_OVER        BTTS                   A        2g
  Ajax v Twente                        BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  Sparta Rotterdam v Excelsior         BTTS_OVER        BTTS                   H        1g
  Vitesse v Nijmegen                   BTTS_OVER        BTTS                   D        0g
  PSV Eindhoven v Vitesse              BTTS_OVER        OVER_25                H        1g
  Sparta Rotterdam v Waalwijk          BTTS_OVER        BOTH_OVER25_BTTS       D        0g
  FC Emmen v PSV Eindhoven             DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H        1g
  For Sittard v Heerenveen             AVOID            AVOID_VOLATILE         H        2g
  Feyenoord v Nijmegen                 BTTS_OVER        BTTS                   H        2g
  Utrecht v Excelsior                  BTTS_OVER        BTTS                   H        1g

## Top 20 Clean Hits

  Match                                Type             Subtype                Actual   Goals
  -----------------------------------------------------------------------------------------------
  AZ Alkmaar v Volendam                BTTS_OVER        BOTH_OVER25_BTTS       H        3g
  PSV Eindhoven v Nijmegen             BTTS_OVER        BTTS                   H        3g
  Vitesse v Sparta Rotterdam           BTTS_OVER        OVER_25                A        4g
  Ajax v PSV Eindhoven                 BTTS_OVER        BOTH_OVER25_BTTS       A        3g
  Utrecht v Groningen                  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Twente v Go Ahead Eagles             DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D        2g
  Waalwijk v AZ Alkmaar                BTTS_OVER        BOTH_OVER25_BTTS       H        4g
  Ajax v Vitesse                       BTTS_OVER        OVER_25                D        4g
  Sparta Rotterdam v Twente            BTTS_OVER        OVER_25                D        2g
  Volendam v Utrecht                   BTTS_OVER        BTTS                   A        4g
  FC Emmen v Ajax                      BTTS_OVER        OVER_25                D        6g
  Nijmegen v Waalwijk                  BTTS_OVER        BTTS                   H        7g
  Groningen v For Sittard              AVOID            AVOID_VOLATILE         A        5g
  Heerenveen v Cambuur                 DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H        3g
  Go Ahead Eagles v Vitesse            BTTS_OVER        BTTS                   D        4g
  AZ Alkmaar v Vitesse                 BTTS_OVER        BOTH_OVER25_BTTS       D        2g
  Nijmegen v Ajax                      BTTS_OVER        BTTS                   D        2g
  Utrecht v Feyenoord                  BTTS_OVER        BTTS                   D        2g
  Volendam v Waalwijk                  AVOID            AVOID_VOLATILE         H        3g
  Groningen v Feyenoord                BTTS_OVER        BTTS                   A        3g

## Sample Size Warnings

  ⚠ DIRECTION: only 2 evaluatable matches — interpret with caution.
  ⚠ OBSERVE_ONLY: only 0 evaluatable matches — interpret with caution.
  ⚠ subtype AVOID_VOLATILE: only 0 evaluatable matches.
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