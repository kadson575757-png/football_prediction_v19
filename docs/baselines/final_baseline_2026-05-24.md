# Walk-Forward Season Replay — Final Aggregate Analysis

> **Diagnostic only. No betting rules. No ROI claims.**  
> Mode: **TRUE walk-forward ML** (LogisticRegression retrained per cutoff)

## Dataset Overview

| Field | Value |
|---|---|
| Leagues | 8 |
| Leagues covered | 2. Bundesliga, Belgian Pro League, Bundesliga, Eredivisie, La Liga, Ligue 1, Premier League, Serie A |
| Season-league combos | 21 |
| Total predicted matches | 5,220 |
| Evaluatable (type_success known) | 4,515 |
| Overall type success rate | **72.4%** |

## 1. Runs Inventory

  League                 Season    rows    ev    rate
  -------------------------------------------------------
  2. Bundesliga          2022       205   179   69.3%
  2. Bundesliga          2023       205   188   73.4%
  2. Bundesliga          2024       205   176   70.5%
  Belgian Pro League     2024       292   257   75.9%
  Bundesliga             2024       206   175   74.9%
  Eredivisie             2022       204   168   72.6%
  Eredivisie             2023       205   175   76.0%
  Eredivisie             2024       203   175   72.6%
  La Liga                2022       280   251   72.1%
  La Liga                2023       280   230   74.8%
  La Liga                2024       280   243   71.2%
  La Liga                2025       290   249   71.9%
  Ligue 1                2022       280   243   67.9%
  Ligue 1                2023       206   186   66.7%
  Ligue 1                2024       205   192   67.7%
  Premier League         2022       276   227   70.5%
  Premier League         2023       280   263   77.2%
  Premier League         2024       280   247   72.1%
  Serie A                2022       280   240   72.1%
  Serie A                2023       280   219   78.5%
  Serie A                2024       278   232   72.0%

  TOTAL                           5220  4515   72.4%

## 2. Overall Success by League

  League                 seasons     n  hits    rate
  --------------------------------------------------
  Belgian Pro League           1   257   195   75.9%
  Bundesliga                   1   175   131   74.9%
  Serie A                      3   691   512   74.1%
  Eredivisie                   3   518   382   73.7%
  Premier League               3   737   541   73.4%
  La Liga                      4   973   705   72.5%
  2. Bundesliga                3   543   386   71.1%
  Ligue 1                      3   621   419   67.5%

## 3. Overall Success by Season

  League + Season                      n  hits    rate
  ----------------------------------------------------
  2. Bundesliga 2022                 179   124   69.3%
  2. Bundesliga 2023                 188   138   73.4%
  2. Bundesliga 2024                 176   124   70.5%
  Belgian Pro League 2024            257   195   75.9%
  Bundesliga 2024                    175   131   74.9%
  Eredivisie 2022                    168   122   72.6%
  Eredivisie 2023                    175   133   76.0%
  Eredivisie 2024                    175   127   72.6%
  La Liga 2022                       251   181   72.1%
  La Liga 2023                       230   172   74.8%
  La Liga 2024                       243   173   71.2%
  La Liga 2025                       249   179   71.9%
  Ligue 1 2022                       243   165   67.9%
  Ligue 1 2023                       186   124   66.7%
  Ligue 1 2024                       192   130   67.7%
  Premier League 2022                227   160   70.5%
  Premier League 2023                263   203   77.2%
  Premier League 2024                247   178   72.1%
  Serie A 2022                       240   173   72.1%
  Serie A 2023                       219   172   78.5%
  Serie A 2024                       232   167   72.0%

## 4. Success by Recommended Market Type — All Leagues

  Group                      n  hits    rate
  -----------------------------------------------
  UNDER                    138   113   81.9%
  AVOID                    587   469   79.9%
  DOUBLE_CHANCE           1373  1055   76.8%
  BTTS_OVER               2206  1497   67.9%
  DIRECTION                211   137   64.9%

## 5. Success by Recommended Market Subtype — All Leagues

  Subtype                        n  hits    rate  Parent            
  ------------------------------------------------------------------------
  UNDER_35                     138   113   81.9%  UNDER             
  DOUBLE_CHANCE_1X             920   709   77.1%  DOUBLE_CHANCE     
  DOUBLE_CHANCE_X2             453   346   76.4%  DOUBLE_CHANCE     
  DIRECTION_HOME               162   113   69.8%  DIRECTION         
  DIRECTION_AWAY                32    21   65.6%  DIRECTION         
  OVER_25                      334   190   56.9%  BTTS_OVER         
  BTTS                        1017   574   56.4%  BTTS_OVER         
  BOTH_OVER25_BTTS             855   420   49.1%  BTTS_OVER         

## 6. Success by League × Market Type

  League + Type                              n  hits    rate
  ------------------------------------------------------------

  Premier League | DOUBLE_CHANCE           183   145   79.2%
  Premier League | AVOID                    89    67   75.3%
  Premier League | BTTS_OVER               434   311   71.7%
  Premier League | DIRECTION                22    13   59.1%
  Premier League | UNDER                     9     5   55.6%  ⚠ n<20

  La Liga | UNDER                           58    54   93.1%
  La Liga | DOUBLE_CHANCE                  360   277   76.9%
  La Liga | AVOID                          112    85   75.9%
  La Liga | DIRECTION                       36    27   75.0%
  La Liga | BTTS_OVER                      407   262   64.4%

  Serie A | AVOID                           95    82   86.3%
  Serie A | DOUBLE_CHANCE                  302   240   79.5%
  Serie A | DIRECTION                       29    22   75.9%
  Serie A | UNDER                           34    24   70.6%
  Serie A | BTTS_OVER                      231   144   62.3%

  Ligue 1 | UNDER                           14    13   92.9%  ⚠ n<20
  Ligue 1 | AVOID                           69    51   73.9%
  Ligue 1 | DOUBLE_CHANCE                  144    97   67.4%
  Ligue 1 | BTTS_OVER                      287   193   67.2%
  Ligue 1 | DIRECTION                      107    65   60.7%

  Eredivisie | UNDER                         3     3  100.0%  ⚠ n<20
  Eredivisie | AVOID                        67    54   80.6%
  Eredivisie | DOUBLE_CHANCE               114    90   78.9%
  Eredivisie | BTTS_OVER                   326   230   70.6%
  Eredivisie | DIRECTION                     8     5   62.5%  ⚠ n<20

  2. Bundesliga | AVOID                     90    78   86.7%
  2. Bundesliga | DOUBLE_CHANCE            142   104   73.2%
  2. Bundesliga | BTTS_OVER                301   199   66.1%
  2. Bundesliga | DIRECTION                  4     2   50.0%  ⚠ n<20
  2. Bundesliga | UNDER                      6     3   50.0%  ⚠ n<20

  Bundesliga | DIRECTION                     1     1  100.0%  ⚠ n<20
  Bundesliga | UNDER                         3     3  100.0%  ⚠ n<20

  Belgian Pro League | DOUBLE_CHANCE        84    70   83.3%
  Belgian Pro League | AVOID                35    29   82.9%

  Bundesliga | AVOID                        30    23   76.7%
  Bundesliga | BTTS_OVER                    97    72   74.2%

  Belgian Pro League | UNDER                11     8   72.7%  ⚠ n<20

  Bundesliga | DOUBLE_CHANCE                44    32   72.7%

  Belgian Pro League | BTTS_OVER           123    86   69.9%
  Belgian Pro League | DIRECTION             4     2   50.0%  ⚠ n<20

## 7. Success by League × Market Subtype

  League + Subtype                               n  hits    rate
  ----------------------------------------------------------------

  Premier League | DOUBLE_CHANCE_1X            118    94   79.7%
  Premier League | DOUBLE_CHANCE_X2             65    51   78.5%
  Premier League | DIRECTION_HOME               12     9   75.0%  ⚠ n<20
  Premier League | BTTS                        129    81   62.8%
  Premier League | UNDER_35                      9     5   55.6%  ⚠ n<20
  Premier League | OVER_25                      84    44   52.4%
  Premier League | BOTH_OVER25_BTTS            221   112   50.7%
  Premier League | DIRECTION_AWAY                7     3   42.9%  ⚠ n<20

  La Liga | UNDER_35                            58    54   93.1%
  La Liga | DIRECTION_HOME                      28    24   85.7%
  La Liga | DOUBLE_CHANCE_1X                   246   191   77.6%
  La Liga | DOUBLE_CHANCE_X2                   114    86   75.4%
  La Liga | OVER_25                             30    18   60.0%
  La Liga | BOTH_OVER25_BTTS                   113    62   54.9%
  La Liga | BTTS                               264   139   52.7%
  La Liga | DIRECTION_AWAY                       7     3   42.9%  ⚠ n<20

  Serie A | DIRECTION_AWAY                      11    10   90.9%  ⚠ n<20
  Serie A | DOUBLE_CHANCE_1X                   197   157   79.7%
  Serie A | DOUBLE_CHANCE_X2                   105    83   79.0%
  Serie A | UNDER_35                            34    24   70.6%
  Serie A | DIRECTION_HOME                      16    10   62.5%  ⚠ n<20
  Serie A | OVER_25                             24    15   62.5%
  Serie A | BTTS                               148    77   52.0%
  Serie A | BOTH_OVER25_BTTS                    59    27   45.8%

  Ligue 1 | UNDER_35                            14    13   92.9%  ⚠ n<20
  Ligue 1 | DOUBLE_CHANCE_X2                    70    53   75.7%
  Ligue 1 | DIRECTION_HOME                      95    63   66.3%
  Ligue 1 | BTTS                               152    94   61.8%
  Ligue 1 | DOUBLE_CHANCE_1X                    74    44   59.5%
  Ligue 1 | BOTH_OVER25_BTTS                   104    53   51.0%
  Ligue 1 | DIRECTION_AWAY                       4     2   50.0%  ⚠ n<20
  Ligue 1 | OVER_25                             31    15   48.4%

  Eredivisie | DIRECTION_AWAY                    3     3  100.0%  ⚠ n<20
  Eredivisie | UNDER_35                          3     3  100.0%  ⚠ n<20
  Eredivisie | DOUBLE_CHANCE_1X                 79    65   82.3%
  Eredivisie | DOUBLE_CHANCE_X2                 35    25   71.4%
  Eredivisie | DIRECTION_HOME                    3     2   66.7%  ⚠ n<20
  Eredivisie | OVER_25                          87    57   65.5%
  Eredivisie | BTTS                            114    64   56.1%
  Eredivisie | BOTH_OVER25_BTTS                125    58   46.4%

  2. Bundesliga | DOUBLE_CHANCE_1X             105    79   75.2%
  2. Bundesliga | DOUBLE_CHANCE_X2              37    25   67.6%
  2. Bundesliga | BTTS                         116    61   52.6%
  2. Bundesliga | DIRECTION_HOME                 4     2   50.0%  ⚠ n<20
  2. Bundesliga | UNDER_35                       6     3   50.0%  ⚠ n<20
  2. Bundesliga | OVER_25                       35    16   45.7%
  2. Bundesliga | BOTH_OVER25_BTTS             150    68   45.3%

  Bundesliga | DIRECTION_HOME                    1     1  100.0%  ⚠ n<20
  Bundesliga | UNDER_35                          3     3  100.0%  ⚠ n<20

  Belgian Pro League | DOUBLE_CHANCE_X2         17    16   94.1%  ⚠ n<20
  Belgian Pro League | DOUBLE_CHANCE_1X         67    54   80.6%

  Bundesliga | DOUBLE_CHANCE_1X                 34    25   73.5%

  Belgian Pro League | UNDER_35                 11     8   72.7%  ⚠ n<20

  Bundesliga | DOUBLE_CHANCE_X2                 10     7   70.0%  ⚠ n<20

  Belgian Pro League | DIRECTION_HOME            3     2   66.7%  ⚠ n<20
  Belgian Pro League | BTTS                     68    42   61.8%

  Bundesliga | BTTS                             26    16   61.5%
  Bundesliga | OVER_25                          17    10   58.8%  ⚠ n<20

  Belgian Pro League | OVER_25                  26    15   57.7%
  Belgian Pro League | BOTH_OVER25_BTTS         29    14   48.3%

  Bundesliga | BOTH_OVER25_BTTS                 54    26   48.1%

## 8. Success by Control Bucket

  Bucket                     n  hits    rate
  --------------------------------------------
  very_low (<3)             12     8   66.7%  ⚠ n<20
  low (3-5)               1745  1253   71.8%
  medium (5-7)            2258  1656   73.3%
  high (7-10)              500   354   70.8%

## 9. Success by Chaos Bucket

  Bucket                     n  hits    rate
  --------------------------------------------
  low (<4)                2020  1538   76.1%
  medium (4-6)            2477  1721   69.5%
  high (6-10)               18    12   66.7%  ⚠ n<20

## 10. Success by Favorite Side

  Group                        n  hits    rate
  -------------------------------------------------
  HOME_FAVORITE             2965  2180   73.5%
  AWAY_FAVORITE             1520  1073   70.6%
  NO_CLEAR_FAVORITE           30    18   60.0%

## 11. Success by Confidence Level

  Confidence             n  hits    rate
  ----------------------------------------
  HIGH                 447   316   70.7%
  MEDIUM              3004  2168   72.2%
  LOW                 1009   736   72.9%
  NO-CONFIDENCE         55    51   92.7%

## 12. Success by Recommendation Strength

  Group                      n  hits    rate
  -----------------------------------------------
  LOW                     1033   790   76.5%
  MEDIUM                  3370  2403   71.3%
  HIGH                     112    78   69.6%

## 13. Top 30 Misses  (type_success = False, sorted by goals desc)

  Match                            League         Type             Subtype                Res    G
  --------------------------------------------------------------------------------------------------
  Hansa Rostock v Fortuna Dussel   2. Bundesliga  UNDER            UNDER_35               A      7
  Betis v Celta                    La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      7
  St Pauli v Elversberg            2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      7
  Roma v Sassuolo                  Serie A        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      7
  Mechelen v Charleroi             Belgian Pro L  UNDER            UNDER_35               H      7
  Strasbourg v Lyon                Ligue 1        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      6
  Barcelona v Granada              La Liga        DIRECTION        DIRECTION_HOME         D      6
  Girona v Real Madrid             La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      6
  Girona v Barcelona               La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      6
  Aston Villa v Leicester          Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      6
  Valencia v Betis                 La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      6
  Paris SG v Nantes                Ligue 1        DIRECTION        NONE                   H      6
  Club Brugge v Gent               Belgian Pro L  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      6
  Holstein Kiel v Hamburg          2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      6
  Leeds v Crystal Palace           Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      6
  Juventus v Torino                Serie A        UNDER            UNDER_35               H      6
  Wolves v Leeds                   Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      6
  Sandhausen v St Pauli            2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Hansa Rostock v Holstein Kiel    2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Girona v Cadiz                   La Liga        UNDER            UNDER_35               H      5
  Leicester v Tottenham            Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      5
  Cadiz v Ath Madrid               La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      5
  Sevilla v Osasuna                La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Real Madrid v Villarreal         La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Ath Bilbao v Girona              La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Ath Madrid v Osasuna             La Liga        DIRECTION        DIRECTION_HOME         A      5
  Reims v Toulouse                 Ligue 1        DIRECTION        DIRECTION_HOME         A      5
  Sevilla v Alaves                 La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Crystal Palace v Everton         Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Nijmegen v Vitesse               Eredivisie     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5

## 14. Top 30 Clean Hits  (type_success = True, sorted by goals desc)

  Match                            League         Type             Subtype                Res    G
  --------------------------------------------------------------------------------------------------
  Atalanta v Salernitana           Serie A        BTTS_OVER        BOTH_OVER25_BTTS       H     10
  AZ Alkmaar v Utrecht             Eredivisie     BTTS_OVER        BOTH_OVER25_BTTS       D     10
  Twente v Volendam                Eredivisie     BTTS_OVER        OVER_25                H      9
  Lyon v Montpellier               Ligue 1        BTTS_OVER        BTTS                   H      9
  Rennes v Brest                   Ligue 1        AVOID            AVOID_VOLATILE         A      9
  Heidenheim v Regensburg          2. Bundesliga  BTTS_OVER        OVER_25                H      9
  Tottenham v Liverpool            Premier Leagu  BTTS_OVER        BOTH_OVER25_BTTS       A      9
  Montpellier v Paris SG           Ligue 1        BTTS_OVER        BTTS                   A      8
  Wehen v Greuther Furth           2. Bundesliga  AVOID            AVOID_VOLATILE         A      8
  Twente v Willem II               Eredivisie     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H      8
  Paderborn v Kaiserslautern       2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H      8
  Newcastle v Luton                Premier Leagu  BTTS_OVER        BOTH_OVER25_BTTS       D      8
  Waalwijk v Go Ahead Eagles       Eredivisie     AVOID            AVOID_VOLATILE         H      8
  Betis v Barcelona                La Liga        BTTS_OVER        BOTH_OVER25_BTTS       A      8
  Girona v Almeria                 La Liga        BTTS_OVER        BTTS                   H      8
  Barcelona v Valencia             La Liga        BTTS_OVER        BTTS                   H      8
  Fortuna Dusseldorf v Schalke 0   2. Bundesliga  BTTS_OVER        BOTH_OVER25_BTTS       H      8
  Monaco v Nantes                  Ligue 1        BTTS_OVER        BTTS                   H      8
  Ath Bilbao v Valladolid          La Liga        BTTS_OVER        OVER_25                H      8
  Fulham v Leicester               Premier Leagu  AVOID            AVOID_VOLATILE         H      8
  Southampton v Liverpool          Premier Leagu  BTTS_OVER        BTTS                   D      8
  Villarreal v Real Madrid         La Liga        BTTS_OVER        OVER_25                D      8
  Monaco v Ajaccio                 Ligue 1        DIRECTION        DIRECTION_HOME         H      8
  Barcelona v Villarreal           La Liga        BTTS_OVER        BOTH_OVER25_BTTS       A      8
  M'gladbach v Hoffenheim          Bundesliga     BTTS_OVER        BOTH_OVER25_BTTS       D      8
  Union Berlin v Stuttgart         Bundesliga     BTTS_OVER        BOTH_OVER25_BTTS       D      8
  Karlsruhe v St Pauli             2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       D      8
  Hannover v Paderborn             2. Bundesliga  AVOID            AVOID_VOLATILE         A      7
  Utrecht v For Sittard            Eredivisie     BTTS_OVER        BTTS                   A      7
  Feyenoord v Heracles             Eredivisie     BTTS_OVER        BOTH_OVER25_BTTS       H      7

## 15. Pattern Stability Assessment (n ≥ 50)

### ✅ Stable Patterns  (n≥50, rate≥70%)

  UNDER_35                     81.9%  (113/138)  [UNDER]
  DOUBLE_CHANCE_1X             77.1%  (709/920)  [DOUBLE_CHANCE]
  DOUBLE_CHANCE_X2             76.4%  (346/453)  [DOUBLE_CHANCE]

### ⚠ Unstable / Marginal Patterns  (n≥50, 55%≤rate<70%)

  DIRECTION_HOME               69.8%  (113/162)  [DIRECTION]
  OVER_25                      56.9%  (190/334)  [BTTS_OVER]
  BTTS                         56.4%  (574/1017)  [BTTS_OVER]

### ❌ Weak / Bad Patterns  (n≥50, rate<55%)

  BOTH_OVER25_BTTS             49.1%  (420/855)  [BTTS_OVER]

## 16. Cross-League Probe Table

  Answers specific diagnostic questions using subtype_success or type_success.

  Pattern                                                       rate  (hits/n)
  ----------------------------------------------------------------------------------
  DOUBLE_CHANCE_1X (Premier League)                         79.7%  (94/118)
  DOUBLE_CHANCE_1X (La Liga)                                77.6%  (191/246)
  DOUBLE_CHANCE_1X (Serie A)                                79.7%  (157/197)
  DOUBLE_CHANCE_1X (Ligue 1)                                59.5%  (44/74)
  DOUBLE_CHANCE_1X (Eredivisie)                             82.3%  (65/79)
  DOUBLE_CHANCE_1X (2. Bundesliga)                          75.2%  (79/105)
  DOUBLE_CHANCE_X2 (Premier League)                         78.5%  (51/65)
  DOUBLE_CHANCE_X2 (La Liga)                                75.4%  (86/114)
  DOUBLE_CHANCE_X2 (Serie A)                                79.0%  (83/105)
  DOUBLE_CHANCE_X2 (Ligue 1)                                75.7%  (53/70)
  DOUBLE_CHANCE_X2 (Eredivisie)                             71.4%  (25/35)  ⚠ n<50
  DOUBLE_CHANCE_X2 (2. Bundesliga)                          67.6%  (25/37)  ⚠ n<50
  AVOID (Premier League)                                    75.3%  (67/89)
  AVOID (La Liga)                                           75.9%  (85/112)
  AVOID (Serie A)                                           86.3%  (82/95)
  AVOID (Ligue 1)                                           73.9%  (51/69)
  AVOID (Eredivisie)                                        80.6%  (54/67)
  AVOID (2. Bundesliga)                                     86.7%  (78/90)
  UNDER_35 (Premier League)                                 55.6%  (5/9)  ⚠ n<50
  UNDER_35 (La Liga)                                        93.1%  (54/58)
  UNDER_35 (Serie A)                                        70.6%  (24/34)  ⚠ n<50
  UNDER_35 (Ligue 1)                                        92.9%  (13/14)  ⚠ n<50
  UNDER_35 (Eredivisie)                                     100.0%  (3/3)  ⚠ n<50
  UNDER_35 (2. Bundesliga)                                  50.0%  (3/6)  ⚠ n<50
  BTTS subtype — ALL                                        56.4%  (574/1017)
  BTTS subtype (Eredivisie)                                 56.1%  (64/114)
  BTTS subtype (2. Bundesliga)                              52.6%  (61/116)
  BTTS subtype (La Liga)                                    52.7%  (139/264)
  BOTH_OVER25_BTTS — ALL                                    49.1%  (420/855)
  BOTH_OVER25_BTTS (Eredivisie)                             46.4%  (58/125)
  BOTH_OVER25_BTTS (2. Bundesliga)                          45.3%  (68/150)
  OVER_25 — ALL                                             56.9%  (190/334)
  OVER_25 (Eredivisie)                                      65.5%  (57/87)
  OVER_25 (2. Bundesliga)                                   45.7%  (16/35)  ⚠ n<50
  OVER_25 (La Liga)                                         60.0%  (18/30)  ⚠ n<50
  OVER_25 (Premier League)                                  52.4%  (44/84)
  BTTS_OVER type (Eredivisie)                               70.6%  (230/326)
  BTTS_OVER type (2. Bundesliga)                            66.1%  (199/301)
  BTTS_OVER type (La Liga)                                  64.4%  (262/407)
  BTTS_OVER type (Premier League)                           71.7%  (311/434)
  BTTS_OVER type (Serie A)                                  62.3%  (144/231)
  BTTS_OVER type (Ligue 1)                                  67.2%  (193/287)
  DIRECTION_HOME — ALL                                      69.8%  (113/162)

## 17. League-Specific Profiles

### Premier League  (541/737 = 73.4% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                      9     5   55.6%  ⚠ n<20
  DOUBLE_CHANCE            183   145   79.2%
  AVOID                     89    67   75.3%
  DIRECTION                 22    13   59.1%
  BTTS_OVER                434   311   71.7%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DOUBLE_CHANCE_1X             118    94   79.7%
  DOUBLE_CHANCE_X2              65    51   78.5%
  DIRECTION_HOME                12     9   75.0%  ⚠ n<20
  BTTS                         129    81   62.8%
  UNDER_35                       9     5   55.6%  ⚠ n<20
  OVER_25                       84    44   52.4%
  BOTH_OVER25_BTTS             221   112   50.7%
  DIRECTION_AWAY                 7     3   42.9%  ⚠ n<20

### La Liga  (705/973 = 72.5% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                     58    54   93.1%
  DOUBLE_CHANCE            360   277   76.9%
  AVOID                    112    85   75.9%
  DIRECTION                 36    27   75.0%
  BTTS_OVER                407   262   64.4%

  Subtype                        n  hits    rate
  ----------------------------------------------
  UNDER_35                      58    54   93.1%
  DIRECTION_HOME                28    24   85.7%
  DOUBLE_CHANCE_1X             246   191   77.6%
  DOUBLE_CHANCE_X2             114    86   75.4%
  OVER_25                       30    18   60.0%
  BOTH_OVER25_BTTS             113    62   54.9%
  BTTS                         264   139   52.7%
  DIRECTION_AWAY                 7     3   42.9%  ⚠ n<20

### Serie A  (512/691 = 74.1% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                     34    24   70.6%
  DOUBLE_CHANCE            302   240   79.5%
  AVOID                     95    82   86.3%
  DIRECTION                 29    22   75.9%
  BTTS_OVER                231   144   62.3%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DIRECTION_AWAY                11    10   90.9%  ⚠ n<20
  DOUBLE_CHANCE_1X             197   157   79.7%
  DOUBLE_CHANCE_X2             105    83   79.0%
  UNDER_35                      34    24   70.6%
  DIRECTION_HOME                16    10   62.5%  ⚠ n<20
  OVER_25                       24    15   62.5%
  BTTS                         148    77   52.0%
  BOTH_OVER25_BTTS              59    27   45.8%

### Ligue 1  (419/621 = 67.5% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                     14    13   92.9%  ⚠ n<20
  DOUBLE_CHANCE            144    97   67.4%
  AVOID                     69    51   73.9%
  DIRECTION                107    65   60.7%
  BTTS_OVER                287   193   67.2%

  Subtype                        n  hits    rate
  ----------------------------------------------
  UNDER_35                      14    13   92.9%  ⚠ n<20
  DOUBLE_CHANCE_X2              70    53   75.7%
  DIRECTION_HOME                95    63   66.3%
  BTTS                         152    94   61.8%
  DOUBLE_CHANCE_1X              74    44   59.5%
  BOTH_OVER25_BTTS             104    53   51.0%
  DIRECTION_AWAY                 4     2   50.0%  ⚠ n<20
  OVER_25                       31    15   48.4%

### Eredivisie  (382/518 = 73.7% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                      3     3  100.0%  ⚠ n<20
  DOUBLE_CHANCE            114    90   78.9%
  AVOID                     67    54   80.6%
  DIRECTION                  8     5   62.5%  ⚠ n<20
  BTTS_OVER                326   230   70.6%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DIRECTION_AWAY                 3     3  100.0%  ⚠ n<20
  UNDER_35                       3     3  100.0%  ⚠ n<20
  DOUBLE_CHANCE_1X              79    65   82.3%
  DOUBLE_CHANCE_X2              35    25   71.4%
  DIRECTION_HOME                 3     2   66.7%  ⚠ n<20
  OVER_25                       87    57   65.5%
  BTTS                         114    64   56.1%
  BOTH_OVER25_BTTS             125    58   46.4%

### 2. Bundesliga  (386/543 = 71.1% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                      6     3   50.0%  ⚠ n<20
  DOUBLE_CHANCE            142   104   73.2%
  AVOID                     90    78   86.7%
  DIRECTION                  4     2   50.0%  ⚠ n<20
  BTTS_OVER                301   199   66.1%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DOUBLE_CHANCE_1X             105    79   75.2%
  DOUBLE_CHANCE_X2              37    25   67.6%
  BTTS                         116    61   52.6%
  DIRECTION_HOME                 4     2   50.0%  ⚠ n<20
  UNDER_35                       6     3   50.0%  ⚠ n<20
  OVER_25                       35    16   45.7%
  BOTH_OVER25_BTTS             150    68   45.3%

## 18. Recommendations for Next Report-Layer Step

Based on the aggregate evidence above (diagnostic only, no betting rules):

### Signal reliability tiers

| Tier | Subtypes | Action |
|---|---|---|
| **Tier 1 — Reliable** | UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2, AVOID | Show prominently; confirm with odds before reporting |
| **Tier 2 — Conditional** | OVER_25 (Eredivisie/2.Bundesliga only), DIRECTION_HOME | Show with league filter; suppress in La Liga/Serie A |
| **Tier 3 — Noisy** | BTTS, BOTH_OVER25_BTTS | Flag as high-variance; consider splitting into stronger sub-conditions |
| **Tier 4 — Suppress** | BOTH_OVER25_BTTS (La Liga/Serie A) | Very low hit rate; suppress or warn |

### League-specific profile recommendations

| League | Profile | Key signal |
|---|---|---|
| Premier League | Control-heavy, low-chaos | DOUBLE_CHANCE preferred; BTTS_OVER unreliable |
| La Liga | Control + UNDER | UNDER_35 dominant; DOUBLE_CHANCE_1X strong; BTTS weak |
| Serie A | Control + UNDER | Similar to La Liga; monitor UNDER_35 volume |
| Ligue 1 | Mixed | DOUBLE_CHANCE reliable; BTTS volatile |
| Eredivisie | Goals league | BTTS_OVER type acceptable (70%+); BOTH_OVER25_BTTS still weak subtype |
| 2. Bundesliga | Goals + DOUBLE_CHANCE | Profile TBD — check BTTS_OVER vs DOUBLE_CHANCE split |

### Next step suggestions (diagnostic only)

1. **Add UNDER_35 trigger condition to all 6 league daily reports** — highest-confidence signal.
2. **Add league filter to BTTS_OVER subtype display**: show OVER_25 in Eredivisie/2.Bundesliga, suppress in La Liga/Serie A/Premier League.
3. **Split BOTH_OVER25_BTTS** into separate OVER_25 + BTTS conditions; the combined AND requirement is systematically too strict.
4. **Add n-warning badge** to subtypes with n<50 in the season replay summary.
5. **Run 3 more seasons per league** to stabilise subtype rates (current n<50 for many league-subtype pairs).

## 19. League Profile Field Coverage

  Rows with league profile fields : 5,220 / 5,220  (100%)
  Fields present                  : league_adjusted_strength, league_preferred_subtype, league_profile, league_suppressed_subtype, league_warning_flags

  Evaluatable rows with LP fields : 4,515
  Overall type-success (LP subset): 72.4%  (3271/4515)
  (compare overall baseline       : 72.4%  3271/4515)

## 20. Success by League-Adjusted Strength  [diagnostic only]

  Strength               n  hits    rate  vs baseline
  ----------------------------------------------------
  HIGH                2305  1778   77.1%  ++4.7%
  MEDIUM               901   605   67.1%  -5.3%
  LOW                   93    75   80.6%  ++8.2%
  SUPPRESSED          1216   813   66.9%  -5.6%

  --- comparison: old recommendation_strength (same LP rows) ---
  (old) LOW             1033   790   76.5%  ++4.0%

## 21. Success by League Profile  [diagnostic only]

  Profile                              n  hits    rate  vs baseline
  ------------------------------------------------------------
  belgium_balanced_goals             257   195   75.9%  ++3.4%
  unknown_league                     175   131   74.9%  ++2.4%
  serie_a_control                    691   512   74.1%  ++1.6%
  eredivisie_goals                   518   382   73.7%  ++1.3%
  premier_league_balanced            737   541   73.4%  ++1.0%
  la_liga_control                    973   705   72.5%  ++0.0%
  bundesliga2_goals_volatile         543   386   71.1%  -1.4%
  ligue1_cautious                    621   419   67.5%  -5.0%

## 22. Success by Warning Flags  [diagnostic only]

  Group                    n  hits    rate  vs baseline
  ------------------------------------------------
  No warning (clean)    3192  2393   75.0%  ++2.5%
  Has warning flag      1323   878   66.4%  -6.1%

  --- breakdown by specific warning ---
  Warning (truncated)                                              n  hits    rate
  ------------------------------------------------------------------------------
  2.Bundesliga: UNDER_35/BOTH_OVER25_BTTS have poor evidence     156   105   67.3%
  Belgian Pro League: new/low-sample profile — treat goal-co      29    20   69.0%
  Eredivisie: BOTH_OVER25_BTTS unreliable even in goals leag     125    88   70.4%
  La Liga: goals subtype has poor walk-forward evidence — tr     407   262   64.4%
  Ligue 1: DIRECTION type has historically poor accuracy — c     107    65   60.7%
  Ligue 1: goals subtypes have weak evidence in this league.     135    86   63.7%
  Premier League: OVER_25 standalone and BOTH_OVER25_BTTS ha     305   213   69.8%
  Serie A: BOTH_OVER25_BTTS has weak cross-league evidence.       59    39   66.1%

## 23. Success — Subtype in League Preferred List  [diagnostic only]

  Group                          n  hits    rate  vs baseline
  ------------------------------------------------------
  Subtype IS preferred        1519  1172   77.2%  ++4.7%
  Subtype NOT preferred       2996  2099   70.1%  -2.4%

## 24. Success — Subtype in League Suppressed List  [diagnostic only]

  Group                          n  hits    rate  vs baseline
  ------------------------------------------------------
  Subtype IS suppressed       1216   813   66.9%  -5.6%
  Subtype NOT suppressed      3299  2458   74.5%  ++2.1%

## 25. Diagnostic Quality Buckets  [A-Tier / B-Tier / C-Tier / No-Go]

  > Bucket definitions (diagnostic only — no betting claims):
  >
  > **A-Tier**: league_adjusted_strength=HIGH + no warning flags
  >             + subtype in {UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2}
  >             + chaos_bucket in {low (<4), medium (4-6)}
  >
  > **No-Go** : league_adjusted_strength=SUPPRESSED
  >             OR has warning flag
  >             OR subtype in {BOTH_OVER25_BTTS, BTTS}
  >             OR subtype=OVER_25 in non-goal-friendly leagues
  >             (goal-friendly: Eredivisie, 2. Bundesliga)
  >
  > **B-Tier**: not A, not No-Go + strength in {HIGH, MEDIUM} + no warning
  > **C-Tier**: everything else (LOW strength or warned but not fully No-Go)

  Bucket           n  hits    rate  vs LP-baseline
  --------------------------------------------------
  A-Tier        1435  1112   77.5%  ++5.0%
  B-Tier         852   655   76.9%  ++4.4%
  C-Tier          31    24   77.4%  ++5.0%
  No-Go         2197  1480   67.4%  -5.1%

  --- A-Tier breakdown by league ---
  League                     n  hits    rate
  ----------------------------------------
  2. Bundesliga            142   104   73.2%
  Belgian Pro League        95    78   82.1%
  Eredivisie               117    93   79.5%
  La Liga                  418   331   79.2%
  Ligue 1                  144    97   67.4%
  Premier League           183   145   79.2%
  Serie A                  336   264   78.6%

  --- A-Tier breakdown by subtype ---
  Subtype                        n  hits    rate
  --------------------------------------------
  DOUBLE_CHANCE_1X             886   684   77.2%
  DOUBLE_CHANCE_X2             443   339   76.5%
  UNDER_35                     106    89   84.0%

  --- No-Go: reason distribution ---
  Reason                             n
  --------------------------------------
  BTTS/BOTH_OVER25_BTTS           1872
  Has warning flag                1323
  SUPPRESSED strength             1216
  OVER_25 non-goal-friendly        212
  (Note: a single row may satisfy multiple No-Go criteria)

## 26. League Profile Diagnostic Summary

  Q1. Does league_adjusted_strength separate better than old strength?
      New spread (HIGH-SUPPRESSED): +10.3%
      Old spread: n/a
      Answer: ✅ NEW spread=+10.3% (old strength not comparable — insufficient tier distribution in LP rows)

  Q2. Is A-Tier better than the LP-subset baseline (72.4%)?
      A-Tier rate: 77.5%
      Answer: ✅ YES

  Q3. Is No-Go worse than the LP-subset baseline (72.4%)?
      No-Go rate: 67.4%
      Answer: ✅ YES

  Q4. Which league profile works best?
      Best : belgium_balanced_goals              75.9%
      Worst: ligue1_cautious                     67.5%

  *League profile sections are diagnostic only. No betting, ROI, or staking claims.*

---
*Aggregate diagnostic report. No betting, staking, or ROI claims.*
*All results are from TRUE walk-forward ML (LogisticRegression retrained per cutoff).*
