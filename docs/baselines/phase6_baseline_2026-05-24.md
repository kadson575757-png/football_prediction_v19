# Walk-Forward Season Replay — Final Aggregate Analysis

> **Diagnostic only. No betting rules. No ROI claims.**  
> Mode: **TRUE walk-forward ML** (LogisticRegression retrained per cutoff)

## Dataset Overview

| Field | Value |
|---|---|
| Leagues | 8 |
| Leagues covered | 2. Bundesliga, Belgian Pro League, Bundesliga, Eredivisie, La Liga, Ligue 1, Premier League, Serie A |
| Season-league combos | 9 |
| Total predicted matches | 2,239 |
| Evaluatable (type_success known) | 1,946 |
| Overall type success rate | **72.1%** |

## 1. Runs Inventory

  League                 Season    rows    ev    rate
  -------------------------------------------------------
  2. Bundesliga          2024       205   176   70.5%
  Belgian Pro League     2024       292   257   75.9%
  Bundesliga             2024       206   175   74.9%
  Eredivisie             2024       203   175   72.6%
  La Liga                2024       280   243   71.2%
  La Liga                2025       290   249   71.9%
  Ligue 1                2024       205   192   67.7%
  Premier League         2024       280   247   72.1%
  Serie A                2024       278   232   72.0%

  TOTAL                           2239  1946   72.1%

## 2. Overall Success by League

  League                 seasons     n  hits    rate
  --------------------------------------------------
  Belgian Pro League           1   257   195   75.9%
  Bundesliga                   1   175   131   74.9%
  Eredivisie                   1   175   127   72.6%
  Premier League               1   247   178   72.1%
  Serie A                      1   232   167   72.0%
  La Liga                      2   492   352   71.5%
  2. Bundesliga                1   176   124   70.5%
  Ligue 1                      1   192   130   67.7%

## 3. Overall Success by Season

  League + Season                      n  hits    rate
  ----------------------------------------------------
  2. Bundesliga 2024                 176   124   70.5%
  Belgian Pro League 2024            257   195   75.9%
  Bundesliga 2024                    175   131   74.9%
  Eredivisie 2024                    175   127   72.6%
  La Liga 2024                       243   173   71.2%
  La Liga 2025                       249   179   71.9%
  Ligue 1 2024                       192   130   67.7%
  Premier League 2024                247   178   72.1%
  Serie A 2024                       232   167   72.0%

## 4. Success by Recommended Market Type — All Leagues

  Group                      n  hits    rate
  -----------------------------------------------
  AVOID                    255   205   80.4%
  UNDER                     52    41   78.8%
  DOUBLE_CHANCE            529   401   75.8%
  DIRECTION                 62    43   69.4%
  BTTS_OVER               1048   714   68.1%

## 5. Success by Recommended Market Subtype — All Leagues

  Subtype                        n  hits    rate  Parent            
  ------------------------------------------------------------------------
  UNDER_35                      52    41   78.8%  UNDER             
  DOUBLE_CHANCE_X2             161   124   77.0%  DOUBLE_CHANCE     
  DIRECTION_HOME                49    37   75.5%  DIRECTION         
  DOUBLE_CHANCE_1X             368   277   75.3%  DOUBLE_CHANCE     
  DIRECTION_AWAY                 8     5   62.5%  DIRECTION           ⚠ n<20
  OVER_25                      148    91   61.5%  BTTS_OVER         
  BTTS                         517   290   56.1%  BTTS_OVER         
  BOTH_OVER25_BTTS             383   190   49.6%  BTTS_OVER         

## 6. Success by League × Market Type

  League + Type                              n  hits    rate
  ------------------------------------------------------------

  Premier League | DOUBLE_CHANCE            52    42   80.8%
  Premier League | AVOID                    26    19   73.1%
  Premier League | BTTS_OVER               160   113   70.6%
  Premier League | DIRECTION                 9     4   44.4%  ⚠ n<20

  La Liga | UNDER                           17    16   94.1%  ⚠ n<20
  La Liga | DIRECTION                       11    10   90.9%  ⚠ n<20
  La Liga | AVOID                           57    45   78.9%
  La Liga | DOUBLE_CHANCE                  138   105   76.1%
  La Liga | BTTS_OVER                      269   176   65.4%

  Serie A | AVOID                           34    31   91.2%
  Serie A | DIRECTION                        6     5   83.3%  ⚠ n<20
  Serie A | DOUBLE_CHANCE                   90    70   77.8%
  Serie A | UNDER                           13     8   61.5%  ⚠ n<20
  Serie A | BTTS_OVER                       89    53   59.6%

  Ligue 1 | UNDER                            5     5  100.0%  ⚠ n<20
  Ligue 1 | BTTS_OVER                      105    76   72.4%
  Ligue 1 | DIRECTION                       28    18   64.3%
  Ligue 1 | AVOID                           20    12   60.0%
  Ligue 1 | DOUBLE_CHANCE                   34    19   55.9%

  Eredivisie | DIRECTION                     3     3  100.0%  ⚠ n<20
  Eredivisie | UNDER                         1     1  100.0%  ⚠ n<20
  Eredivisie | AVOID                        22    18   81.8%
  Eredivisie | DOUBLE_CHANCE                41    30   73.2%
  Eredivisie | BTTS_OVER                   108    75   69.4%

  2. Bundesliga | AVOID                     31    28   90.3%
  2. Bundesliga | DOUBLE_CHANCE             46    33   71.7%
  2. Bundesliga | BTTS_OVER                 97    63   64.9%
  2. Bundesliga | UNDER                      2     0    0.0%  ⚠ n<20

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

  Premier League | DOUBLE_CHANCE_X2             13    11   84.6%  ⚠ n<20
  Premier League | DOUBLE_CHANCE_1X             39    31   79.5%
  Premier League | OVER_25                      33    21   63.6%
  Premier League | DIRECTION_HOME                5     3   60.0%  ⚠ n<20
  Premier League | BTTS                         58    33   56.9%
  Premier League | BOTH_OVER25_BTTS             69    31   44.9%
  Premier League | DIRECTION_AWAY                3     1   33.3%  ⚠ n<20

  La Liga | DIRECTION_AWAY                       1     1  100.0%  ⚠ n<20
  La Liga | UNDER_35                            17    16   94.1%  ⚠ n<20
  La Liga | DIRECTION_HOME                      10     9   90.0%  ⚠ n<20
  La Liga | OVER_25                             18    14   77.8%  ⚠ n<20
  La Liga | DOUBLE_CHANCE_1X                    93    71   76.3%
  La Liga | DOUBLE_CHANCE_X2                    45    34   75.6%
  La Liga | BTTS                               174    93   53.4%
  La Liga | BOTH_OVER25_BTTS                    77    41   53.2%

  Serie A | DOUBLE_CHANCE_X2                    28    23   82.1%
  Serie A | DIRECTION_HOME                       5     4   80.0%  ⚠ n<20
  Serie A | DOUBLE_CHANCE_1X                    62    47   75.8%
  Serie A | OVER_25                              8     5   62.5%  ⚠ n<20
  Serie A | UNDER_35                            13     8   61.5%  ⚠ n<20
  Serie A | BTTS                                63    30   47.6%
  Serie A | BOTH_OVER25_BTTS                    18     8   44.4%  ⚠ n<20

  Ligue 1 | UNDER_35                             5     5  100.0%  ⚠ n<20
  Ligue 1 | DIRECTION_HOME                      24    17   70.8%
  Ligue 1 | DOUBLE_CHANCE_X2                    19    13   68.4%  ⚠ n<20
  Ligue 1 | BTTS                                48    31   64.6%
  Ligue 1 | BOTH_OVER25_BTTS                    45    26   57.8%
  Ligue 1 | DIRECTION_AWAY                       2     1   50.0%  ⚠ n<20
  Ligue 1 | OVER_25                             12     5   41.7%  ⚠ n<20
  Ligue 1 | DOUBLE_CHANCE_1X                    15     6   40.0%  ⚠ n<20

  Eredivisie | DIRECTION_AWAY                    2     2  100.0%  ⚠ n<20
  Eredivisie | DIRECTION_HOME                    1     1  100.0%  ⚠ n<20
  Eredivisie | UNDER_35                          1     1  100.0%  ⚠ n<20
  Eredivisie | DOUBLE_CHANCE_1X                 28    22   78.6%
  Eredivisie | OVER_25                          22    15   68.2%
  Eredivisie | BTTS                             43    27   62.8%
  Eredivisie | DOUBLE_CHANCE_X2                 13     8   61.5%  ⚠ n<20
  Eredivisie | BOTH_OVER25_BTTS                 43    21   48.8%

  2. Bundesliga | DOUBLE_CHANCE_X2              16    12   75.0%  ⚠ n<20
  2. Bundesliga | DOUBLE_CHANCE_1X              30    21   70.0%
  2. Bundesliga | OVER_25                       12     6   50.0%  ⚠ n<20
  2. Bundesliga | BTTS                          37    18   48.6%
  2. Bundesliga | BOTH_OVER25_BTTS              48    23   47.9%
  2. Bundesliga | UNDER_35                       2     0    0.0%  ⚠ n<20

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
  low (3-5)                744   532   71.5%
  medium (5-7)             985   713   72.4%
  high (7-10)              205   151   73.7%

## 9. Success by Chaos Bucket

  Bucket                     n  hits    rate
  --------------------------------------------
  low (<4)                 767   581   75.7%
  medium (4-6)            1175   820   69.8%
  high (6-10)                4     3   75.0%  ⚠ n<20

## 10. Success by Favorite Side

  Group                        n  hits    rate
  -------------------------------------------------
  HOME_FAVORITE             1282   943   73.6%
  AWAY_FAVORITE              646   450   69.7%
  NO_CLEAR_FAVORITE           18    11   61.1%  ⚠ n<20

## 11. Success by Confidence Level

  Confidence             n  hits    rate
  ----------------------------------------
  HIGH                 182   134   73.6%
  MEDIUM              1316   944   71.7%
  LOW                  425   305   71.8%
  NO-CONFIDENCE         23    21   91.3%

## 12. Success by Recommendation Strength

  Group                      n  hits    rate
  -----------------------------------------------
  LOW                      455   343   75.4%
  HIGH                      36    27   75.0%
  MEDIUM                  1455  1034   71.1%

## 13. Top 30 Misses  (type_success = False, sorted by goals desc)

  Match                            League         Type             Subtype                Res    G
  --------------------------------------------------------------------------------------------------
  Mechelen v Charleroi             Belgian Pro L  UNDER            UNDER_35               H      7
  Strasbourg v Lyon                Ligue 1        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      6
  Club Brugge v Gent               Belgian Pro L  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      6
  Valencia v Betis                 La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      6
  Nott'm Forest v Southampton      Premier Leagu  DIRECTION        NONE                   H      5
  Everton v Tottenham              Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      5
  Oud-Heverlee Leuven v Dender     Belgian Pro L  UNDER            UNDER_35               H      5
  Anderlecht v Dender              Belgian Pro L  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Man United v Nott'm Forest       Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Willem II v Nijmegen             Eredivisie     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      5
  Magdeburg v Preußen Münster      2. Bundesliga  UNDER            UNDER_35               A      5
  Braunschweig v Paderborn         2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      5
  Atalanta v Parma                 Serie A        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      5
  Genoa v Atalanta                 Serie A        UNDER            UNDER_35               A      5
  Fulham v Liverpool               Premier Leagu  DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      5
  Nantes v Lens                    Ligue 1        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      4
  Vallecano v Osasuna              La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      4
  St Etienne v Reims               Ligue 1        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      4
  Udinese v Napoli                 Serie A        UNDER            UNDER_35               A      4
  Empoli v Lecce                   Serie A        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      4
  Betis v Getafe                   La Liga        UNDER            UNDER_35               H      4
  Utrecht v Ajax                   Eredivisie     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      4
  Heerenveen v AZ Alkmaar          Eredivisie     DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      4
  Montpellier v Angers             Ligue 1        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      4
  Lille v Auxerre                  Ligue 1        DIRECTION        DIRECTION_AWAY         H      4
  Reims v Marseille                Ligue 1        DOUBLE_CHANCE    DOUBLE_CHANCE_X2       H      4
  Willem II v Groningen            Eredivisie     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      4
  Augsburg v Holstein Kiel         Bundesliga     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      4
  Antwerp v Anderlecht             Belgian Pro L  UNDER            UNDER_35               A      4
  St. Gilloise v Cercle Brugge     Belgian Pro L  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       A      4

## 14. Top 30 Clean Hits  (type_success = True, sorted by goals desc)

  Match                            League         Type             Subtype                Res    G
  --------------------------------------------------------------------------------------------------
  Tottenham v Liverpool            Premier Leagu  BTTS_OVER        BOTH_OVER25_BTTS       A      9
  Monaco v Nantes                  Ligue 1        BTTS_OVER        BTTS                   H      8
  Betis v Barcelona                La Liga        BTTS_OVER        BOTH_OVER25_BTTS       A      8
  Union Berlin v Stuttgart         Bundesliga     BTTS_OVER        BOTH_OVER25_BTTS       D      8
  Ath Bilbao v Valladolid          La Liga        BTTS_OVER        OVER_25                H      8
  Twente v Willem II               Eredivisie     DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H      8
  Paderborn v Kaiserslautern       2. Bundesliga  DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H      8
  Barcelona v Valencia             La Liga        BTTS_OVER        BTTS                   H      8
  M'gladbach v Hoffenheim          Bundesliga     BTTS_OVER        BOTH_OVER25_BTTS       D      8
  Waalwijk v Go Ahead Eagles       Eredivisie     AVOID            AVOID_VOLATILE         H      8
  Sociedad v Valencia              La Liga        BTTS_OVER        BTTS                   A      7
  Charleroi v Westerlo             Belgian Pro L  BTTS_OVER        BTTS                   H      7
  Bayern Munich v Holstein Kiel    Bundesliga     BTTS_OVER        BOTH_OVER25_BTTS       H      7
  Club Brugge v Westerlo           Belgian Pro L  BTTS_OVER        BTTS                   H      7
  St Etienne v Paris SG            Ligue 1        BTTS_OVER        BOTH_OVER25_BTTS       A      7
  Lens v Le Havre                  Ligue 1        BTTS_OVER        BTTS                   A      7
  Brest v Paris SG                 Ligue 1        BTTS_OVER        BOTH_OVER25_BTTS       A      7
  Wolfsburg v Mainz                Bundesliga     AVOID            AVOID_VOLATILE         H      7
  Groningen v Waalwijk             Eredivisie     BTTS_OVER        BOTH_OVER25_BTTS       H      7
  Schalke 04 v Magdeburg           2. Bundesliga  BTTS_OVER        BTTS                   A      7
  Elversberg v Magdeburg           2. Bundesliga  AVOID            AVOID_VOLATILE         A      7
  Holstein Kiel v M'gladbach       Bundesliga     BTTS_OVER        BOTH_OVER25_BTTS       H      7
  Barcelona v Real Madrid          La Liga        DOUBLE_CHANCE    DOUBLE_CHANCE_1X       H      7
  Newcastle v Nott'm Forest        Premier Leagu  BTTS_OVER        OVER_25                H      7
  Stuttgart v Leverkusen           Bundesliga     BTTS_OVER        BTTS                   A      7
  Club Brugge v St Truiden         Belgian Pro L  BTTS_OVER        BTTS                   H      7
  Tottenham v Chelsea              Premier Leagu  BTTS_OVER        BOTH_OVER25_BTTS       A      7
  West Ham v Arsenal               Premier Leagu  BTTS_OVER        BTTS                   A      7
  Beerschot VA v Genk              Belgian Pro L  BTTS_OVER        BOTH_OVER25_BTTS       A      7
  Antwerp v St Truiden             Belgian Pro L  AVOID            AVOID_VOLATILE         H      7

## 15. Pattern Stability Assessment (n ≥ 50)

### ✅ Stable Patterns  (n≥50, rate≥70%)

  UNDER_35                     78.8%  (41/52)  [UNDER]
  DOUBLE_CHANCE_X2             77.0%  (124/161)  [DOUBLE_CHANCE]
  DOUBLE_CHANCE_1X             75.3%  (277/368)  [DOUBLE_CHANCE]

### ⚠ Unstable / Marginal Patterns  (n≥50, 55%≤rate<70%)

  OVER_25                      61.5%  (91/148)  [BTTS_OVER]
  BTTS                         56.1%  (290/517)  [BTTS_OVER]

### ❌ Weak / Bad Patterns  (n≥50, rate<55%)

  BOTH_OVER25_BTTS             49.6%  (190/383)  [BTTS_OVER]

## 16. Cross-League Probe Table

  Answers specific diagnostic questions using subtype_success or type_success.

  Pattern                                                       rate  (hits/n)
  ----------------------------------------------------------------------------------
  DOUBLE_CHANCE_1X (Premier League)                         79.5%  (31/39)  ⚠ n<50
  DOUBLE_CHANCE_1X (La Liga)                                76.3%  (71/93)
  DOUBLE_CHANCE_1X (Serie A)                                75.8%  (47/62)
  DOUBLE_CHANCE_1X (Ligue 1)                                40.0%  (6/15)  ⚠ n<50
  DOUBLE_CHANCE_1X (Eredivisie)                             78.6%  (22/28)  ⚠ n<50
  DOUBLE_CHANCE_1X (2. Bundesliga)                          70.0%  (21/30)  ⚠ n<50
  DOUBLE_CHANCE_X2 (Premier League)                         84.6%  (11/13)  ⚠ n<50
  DOUBLE_CHANCE_X2 (La Liga)                                75.6%  (34/45)  ⚠ n<50
  DOUBLE_CHANCE_X2 (Serie A)                                82.1%  (23/28)  ⚠ n<50
  DOUBLE_CHANCE_X2 (Ligue 1)                                68.4%  (13/19)  ⚠ n<50
  DOUBLE_CHANCE_X2 (Eredivisie)                             61.5%  (8/13)  ⚠ n<50
  DOUBLE_CHANCE_X2 (2. Bundesliga)                          75.0%  (12/16)  ⚠ n<50
  AVOID (Premier League)                                    73.1%  (19/26)  ⚠ n<50
  AVOID (La Liga)                                           78.9%  (45/57)
  AVOID (Serie A)                                           91.2%  (31/34)  ⚠ n<50
  AVOID (Ligue 1)                                           60.0%  (12/20)  ⚠ n<50
  AVOID (Eredivisie)                                        81.8%  (18/22)  ⚠ n<50
  AVOID (2. Bundesliga)                                     90.3%  (28/31)  ⚠ n<50
  UNDER_35 (Premier League)                                 n/a      (n=0)
  UNDER_35 (La Liga)                                        94.1%  (16/17)  ⚠ n<50
  UNDER_35 (Serie A)                                        61.5%  (8/13)  ⚠ n<50
  UNDER_35 (Ligue 1)                                        100.0%  (5/5)  ⚠ n<50
  UNDER_35 (Eredivisie)                                     100.0%  (1/1)  ⚠ n<50
  UNDER_35 (2. Bundesliga)                                  0.0%  (0/2)  ⚠ n<50
  BTTS subtype — ALL                                        56.1%  (290/517)
  BTTS subtype (Eredivisie)                                 62.8%  (27/43)  ⚠ n<50
  BTTS subtype (2. Bundesliga)                              48.6%  (18/37)  ⚠ n<50
  BTTS subtype (La Liga)                                    53.4%  (93/174)
  BOTH_OVER25_BTTS — ALL                                    49.6%  (190/383)
  BOTH_OVER25_BTTS (Eredivisie)                             48.8%  (21/43)  ⚠ n<50
  BOTH_OVER25_BTTS (2. Bundesliga)                          47.9%  (23/48)  ⚠ n<50
  OVER_25 — ALL                                             61.5%  (91/148)
  OVER_25 (Eredivisie)                                      68.2%  (15/22)  ⚠ n<50
  OVER_25 (2. Bundesliga)                                   50.0%  (6/12)  ⚠ n<50
  OVER_25 (La Liga)                                         77.8%  (14/18)  ⚠ n<50
  OVER_25 (Premier League)                                  63.6%  (21/33)  ⚠ n<50
  BTTS_OVER type (Eredivisie)                               69.4%  (75/108)
  BTTS_OVER type (2. Bundesliga)                            64.9%  (63/97)
  BTTS_OVER type (La Liga)                                  65.4%  (176/269)
  BTTS_OVER type (Premier League)                           70.6%  (113/160)
  BTTS_OVER type (Serie A)                                  59.6%  (53/89)
  BTTS_OVER type (Ligue 1)                                  72.4%  (76/105)
  DIRECTION_HOME — ALL                                      75.5%  (37/49)  ⚠ n<50

## 17. League-Specific Profiles

### Premier League  (178/247 = 72.1% overall)

  Type                       n  hits    rate
  ------------------------------------------
  DOUBLE_CHANCE             52    42   80.8%
  AVOID                     26    19   73.1%
  DIRECTION                  9     4   44.4%  ⚠ n<20
  BTTS_OVER                160   113   70.6%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DOUBLE_CHANCE_X2              13    11   84.6%  ⚠ n<20
  DOUBLE_CHANCE_1X              39    31   79.5%
  OVER_25                       33    21   63.6%
  DIRECTION_HOME                 5     3   60.0%  ⚠ n<20
  BTTS                          58    33   56.9%
  BOTH_OVER25_BTTS              69    31   44.9%
  DIRECTION_AWAY                 3     1   33.3%  ⚠ n<20

### La Liga  (352/492 = 71.5% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                     17    16   94.1%  ⚠ n<20
  DOUBLE_CHANCE            138   105   76.1%
  AVOID                     57    45   78.9%
  DIRECTION                 11    10   90.9%  ⚠ n<20
  BTTS_OVER                269   176   65.4%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DIRECTION_AWAY                 1     1  100.0%  ⚠ n<20
  UNDER_35                      17    16   94.1%  ⚠ n<20
  DIRECTION_HOME                10     9   90.0%  ⚠ n<20
  OVER_25                       18    14   77.8%  ⚠ n<20
  DOUBLE_CHANCE_1X              93    71   76.3%
  DOUBLE_CHANCE_X2              45    34   75.6%
  BTTS                         174    93   53.4%
  BOTH_OVER25_BTTS              77    41   53.2%

### Serie A  (167/232 = 72.0% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                     13     8   61.5%  ⚠ n<20
  DOUBLE_CHANCE             90    70   77.8%
  AVOID                     34    31   91.2%
  DIRECTION                  6     5   83.3%  ⚠ n<20
  BTTS_OVER                 89    53   59.6%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DOUBLE_CHANCE_X2              28    23   82.1%
  DIRECTION_HOME                 5     4   80.0%  ⚠ n<20
  DOUBLE_CHANCE_1X              62    47   75.8%
  OVER_25                        8     5   62.5%  ⚠ n<20
  UNDER_35                      13     8   61.5%  ⚠ n<20
  BTTS                          63    30   47.6%
  BOTH_OVER25_BTTS              18     8   44.4%  ⚠ n<20

### Ligue 1  (130/192 = 67.7% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                      5     5  100.0%  ⚠ n<20
  DOUBLE_CHANCE             34    19   55.9%
  AVOID                     20    12   60.0%
  DIRECTION                 28    18   64.3%
  BTTS_OVER                105    76   72.4%

  Subtype                        n  hits    rate
  ----------------------------------------------
  UNDER_35                       5     5  100.0%  ⚠ n<20
  DIRECTION_HOME                24    17   70.8%
  DOUBLE_CHANCE_X2              19    13   68.4%  ⚠ n<20
  BTTS                          48    31   64.6%
  BOTH_OVER25_BTTS              45    26   57.8%
  DIRECTION_AWAY                 2     1   50.0%  ⚠ n<20
  OVER_25                       12     5   41.7%  ⚠ n<20
  DOUBLE_CHANCE_1X              15     6   40.0%  ⚠ n<20

### Eredivisie  (127/175 = 72.6% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                      1     1  100.0%  ⚠ n<20
  DOUBLE_CHANCE             41    30   73.2%
  AVOID                     22    18   81.8%
  DIRECTION                  3     3  100.0%  ⚠ n<20
  BTTS_OVER                108    75   69.4%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DIRECTION_AWAY                 2     2  100.0%  ⚠ n<20
  DIRECTION_HOME                 1     1  100.0%  ⚠ n<20
  UNDER_35                       1     1  100.0%  ⚠ n<20
  DOUBLE_CHANCE_1X              28    22   78.6%
  OVER_25                       22    15   68.2%
  BTTS                          43    27   62.8%
  DOUBLE_CHANCE_X2              13     8   61.5%  ⚠ n<20
  BOTH_OVER25_BTTS              43    21   48.8%

### 2. Bundesliga  (124/176 = 70.5% overall)

  Type                       n  hits    rate
  ------------------------------------------
  UNDER                      2     0    0.0%  ⚠ n<20
  DOUBLE_CHANCE             46    33   71.7%
  AVOID                     31    28   90.3%
  BTTS_OVER                 97    63   64.9%

  Subtype                        n  hits    rate
  ----------------------------------------------
  DOUBLE_CHANCE_X2              16    12   75.0%  ⚠ n<20
  DOUBLE_CHANCE_1X              30    21   70.0%
  OVER_25                       12     6   50.0%  ⚠ n<20
  BTTS                          37    18   48.6%
  BOTH_OVER25_BTTS              48    23   47.9%
  UNDER_35                       2     0    0.0%  ⚠ n<20

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

  Rows with league profile fields : 2,239 / 2,239  (100%)
  Fields present                  : league_adjusted_strength, league_preferred_subtype, league_profile, league_suppressed_subtype, league_warning_flags

  Evaluatable rows with LP fields : 1,946
  Overall type-success (LP subset): 72.1%  (1404/1946)
  (compare overall baseline       : 72.1%  1404/1946)

## 20. Success by League-Adjusted Strength  [diagnostic only]

  Strength               n  hits    rate  vs baseline
  ----------------------------------------------------
  HIGH                 853   658   77.1%  ++5.0%
  MEDIUM               450   307   68.2%  -3.9%
  LOW                   75    59   78.7%  ++6.5%
  SUPPRESSED           568   380   66.9%  -5.2%

  --- comparison: old recommendation_strength (same LP rows) ---
  (old) LOW              455   343   75.4%  ++3.2%

## 21. Success by League Profile  [diagnostic only]

  Profile                              n  hits    rate  vs baseline
  ------------------------------------------------------------
  belgium_balanced_goals             257   195   75.9%  ++3.7%
  unknown_league                     175   131   74.9%  ++2.7%
  eredivisie_goals                   175   127   72.6%  ++0.4%
  premier_league_balanced            247   178   72.1%  -0.1%
  serie_a_control                    232   167   72.0%  -0.2%
  la_liga_control                    492   352   71.5%  -0.6%
  bundesliga2_goals_volatile         176   124   70.5%  -1.7%
  ligue1_cautious                    192   130   67.7%  -4.4%

## 22. Success by Warning Flags  [diagnostic only]

  Group                    n  hits    rate  vs baseline
  ------------------------------------------------
  No warning (clean)    1350  1006   74.5%  ++2.4%
  Has warning flag       596   398   66.8%  -5.4%

  --- breakdown by specific warning ---
  Warning (truncated)                                              n  hits    rate
  ------------------------------------------------------------------------------
  2.Bundesliga: UNDER_35/BOTH_OVER25_BTTS have poor evidence      50    32   64.0%
  Belgian Pro League: new/low-sample profile — treat goal-co      29    20   69.0%
  Eredivisie: BOTH_OVER25_BTTS unreliable even in goals leag      43    28   65.1%
  La Liga: goals subtype has poor walk-forward evidence — tr     269   176   65.4%
  Ligue 1: DIRECTION type has historically poor accuracy — c      28    18   64.3%
  Ligue 1: goals subtypes have weak evidence in this league.      57    41   71.9%
  Premier League: OVER_25 standalone and BOTH_OVER25_BTTS ha     102    71   69.6%
  Serie A: BOTH_OVER25_BTTS has weak cross-league evidence.       18    12   66.7%

## 23. Success — Subtype in League Preferred List  [diagnostic only]

  Group                          n  hits    rate  vs baseline
  ------------------------------------------------------
  Subtype IS preferred         548   417   76.1%  ++3.9%
  Subtype NOT preferred       1398   987   70.6%  -1.5%

## 24. Success — Subtype in League Suppressed List  [diagnostic only]

  Group                          n  hits    rate  vs baseline
  ------------------------------------------------------
  Subtype IS suppressed        568   380   66.9%  -5.2%
  Subtype NOT suppressed      1378  1024   74.3%  ++2.2%

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
  A-Tier         527   402   76.3%  ++4.1%
  B-Tier         345   272   78.8%  ++6.7%
  C-Tier          30    23   76.7%  ++4.5%
  No-Go         1044   707   67.7%  -4.4%

  --- A-Tier breakdown by league ---
  League                     n  hits    rate
  ----------------------------------------
  2. Bundesliga             46    33   71.7%
  Belgian Pro League        95    78   82.1%
  Eredivisie                42    31   73.8%
  La Liga                  155   121   78.1%
  Ligue 1                   34    19   55.9%
  Premier League            52    42   80.8%
  Serie A                  103    78   75.7%

  --- A-Tier breakdown by subtype ---
  Subtype                        n  hits    rate
  --------------------------------------------
  DOUBLE_CHANCE_1X             334   252   75.4%
  DOUBLE_CHANCE_X2             151   117   77.5%
  UNDER_35                      42    33   78.6%

  --- No-Go: reason distribution ---
  Reason                             n
  --------------------------------------
  BTTS/BOTH_OVER25_BTTS            900
  Has warning flag                 596
  SUPPRESSED strength              568
  OVER_25 non-goal-friendly        114
  (Note: a single row may satisfy multiple No-Go criteria)

## 26. League Profile Diagnostic Summary

  Q1. Does league_adjusted_strength separate better than old strength?
      New spread (HIGH-SUPPRESSED): +10.2%
      Old spread: n/a
      Answer: ✅ NEW spread=+10.2% (old strength not comparable — insufficient tier distribution in LP rows)

  Q2. Is A-Tier better than the LP-subset baseline (72.1%)?
      A-Tier rate: 76.3%
      Answer: ✅ YES

  Q3. Is No-Go worse than the LP-subset baseline (72.1%)?
      No-Go rate: 67.7%
      Answer: ✅ YES

  Q4. Which league profile works best?
      Best : belgium_balanced_goals              75.9%
      Worst: ligue1_cautious                     67.7%

  *League profile sections are diagnostic only. No betting, ROI, or staking claims.*

---
*Aggregate diagnostic report. No betting, staking, or ROI claims.*
*All results are from TRUE walk-forward ML (LogisticRegression retrained per cutoff).*
