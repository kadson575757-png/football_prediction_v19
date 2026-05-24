# Daily Recommendation Evaluation Summary

- Total pre-match rows      : 31
- Verified scores matched   : 18  (verified=yes only)
- Unverified / not matched  : 13  (excluded from all calculations)
- Evaluatable rows          : 18  (matched + not OBSERVE_ONLY)

*All success rates are based on verified=yes rows only.*


## Success Rate by Recommended Market Type

Type                n hits    rate  Notes
-------------------------------------------------------
  AVOID             4    4  100.0%  
  BTTS_OVER         8    5   62.5%  OR-success=5/8 (62.5%)  over2.5=4/8 (50.0%)  btts=5/8 (62.5%)
  DOUBLE_CHANCE     2    2  100.0%  
  UNDER             4    3   75.0%  under25_hit=3/4

### BTTS_OVER Detail (OR logic)

  Success rule   : actual_over2.5  OR  actual_btts  (either is sufficient)
  OR success     : 5/8  (62.5%)
  Over 2.5 alone : 4/8  (50.0%)
  BTTS alone     : 5/8  (62.5%)
  Note: All Over2.5 hits were also BTTS hits in this sample — OR rate equals BTTS-only rate (62.5%). Over2.5 added no independent lift here.


## Success Rate by Recommended Market Subtype

  Subtype success uses a precise, single-condition rule per subtype (e.g. OVER_25 = total > 2.5 only; BTTS = both scored only).

  Subtype                   n hits    rate  Parent type
  ------------------------------------------------------------
  BOTH_OVER25_BTTS          3    2   66.7%  BTTS_OVER
  BTTS                      3    2   66.7%  BTTS_OVER
  DOUBLE_CHANCE_1X          1    1  100.0%  DOUBLE_CHANCE
  DOUBLE_CHANCE_X2          1    1  100.0%  DOUBLE_CHANCE
  OVER_25                   2    1   50.0%  BTTS_OVER
  UNDER_35                  4    3   75.0%  UNDER

  ### BTTS_OVER Split Comparison

  BTTS_OVER (type-level OR):  5/8  (62.5%)
  Subtype BOTH_OVER25_BTTS    : 2/3  (66.7%)
  Subtype BTTS                : 2/3  (66.7%)
  Subtype OVER_25             : 1/2  (50.0%)
  Interpretation: a subtype with a higher rate than the OR rate represents a more reliable narrower call.

## Success Rate by Market Tier

  Tier              n hits    rate
  ------------------------------------
  A_TIER            6    5   83.3%
  B_TIER            6    6  100.0%
  HARD_NO_GO        6    3   50.0%

  A_TIER + B_TIER combined: 11/12 (91.7%)

## Success Rate by Market Tier Score Bucket

  Score bucket      n hits    rate
  ------------------------------------
  80+               6    5   83.3%
  70-79             6    6  100.0%
  <50               6    3   50.0%

## Success Rate by League

League                  n hits    rate
----------------------------------------
  EPL                   4    3   75.0%
  Eredivisie            5    5  100.0%
  La Liga               9    6   66.7%

## Success Rate by Confidence

Confidence          n hits    rate
----------------------------------------
  HIGH              1    1  100.0%
  LOW              11    7   63.6%
  MEDIUM            4    4  100.0%
  NO-CONFIDENCE     2    2  100.0%

## Success Rate by Control Bucket (0-10 scale)

Control               n hits    rate
----------------------------------------
  low (3-5)           2    2  100.0%
  medium (5-7)        1    1  100.0%
  very_low (<3)      15   11   73.3%

## Success Rate by Chaos Bucket (0-10 scale)

Chaos                 n hits    rate
----------------------------------------
  low (<4)           15   12   80.0%
  medium (4-6)        3    2   66.7%

## Top Misses

Match                                  Type           Read                             Conf           Actual
--------------------------------------------------------------------------------------------------------------
  Leeds vs Brighton & Hove Albion        BTTS_OVER      goals_profile_preferred_over_h   LOW            H (1g)
  Sevilla vs Real Madrid                 BTTS_OVER      goals_profile_preferred_over_h   LOW            A (1g)
  Sociedad vs Valencia                   UNDER          under_profile_low_chaos_weak_b   LOW            A (7g)
  Levante vs Mallorca                    BTTS_OVER      goals_profile_preferred_over_h   LOW            H (2g)

## Best-Performing Recommendation Types
  AVOID            100.0% (4/4)
  DOUBLE_CHANCE    100.0% (2/2)
  UNDER            75.0% (3/4)

## Worst-Performing Recommendation Types
  BTTS_OVER        62.5% (5/8)
  UNDER            75.0% (3/4)
  AVOID            100.0% (4/4)

## Recommended Market Layer Assessment

Overall evaluatable success rate: 77.8% (14/18)

Verdict: STRONG — recommended market layer is performing well above a naive baseline.

*This is a diagnostic-only evaluation. No betting claims.*