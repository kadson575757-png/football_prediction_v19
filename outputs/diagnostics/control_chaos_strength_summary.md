# Control / Chaos x Favorite Strength Audit

Diagnostic only. No betting rules, paper-test rules, ledger entries, ROI claims, or market recommendations.

## Data Sources Used
- `data\processed\all_leagues_2021_2025_clean.csv`
- `data\processed\mls_matches_clean_with_odds.csv`
- Matches analyzed after filtering and warm-up: **8782**
- Control/chaos scale used: **0-10**
- Feature replay: each match used only same-league matches before its match date.
- Model replay: league-specific bundles where available (MLS, D2, Eredivisie), otherwise best available combined top-5 model.

## Main H1 Table: Home Favorite Strength x Control
| home_fav_bucket | control_bucket | N | Sample | Home win % | Under 3.5 % | Over 2.5 % | BTTS % | Fav win + U3.5 % | Avg goals | Top scores |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| very_strong_home_fav | low_control | 18 | ignore (<50) | 11.1 | 77.8 | 22.2 | 66.7 | 11.1 | 2.22 | 1-1:8, 0-1:3, 2-0:2, 2-2:2, 2-3:1, 1-3:1, 0-0:1 |
| very_strong_home_fav | medium_control | 44 | ignore (<50) | 15.9 | 68.2 | 43.2 | 65.9 | 11.4 | 2.64 | 1-1:10, 2-2:8, 0-0:7, 1-2:5, 2-0:4, 0-2:2, 1-3:1, 0-1:1, 3-4:1, 3-3:1 |
| very_strong_home_fav | high_control | 1234 | preferred | 76.5 | 59.3 | 62.9 | 49.0 | 42.3 | 3.25 | 2-0:147, 1-0:133, 2-1:127, 3-0:115, 3-1:93, 1-1:83, 4-0:74, 0-0:52, 2-2:43, 4-1:42 |
| strong_home_fav | low_control | 136 | preferred | 17.6 | 71.3 | 55.1 | 58.1 | 10.3 | 2.67 | 1-2:23, 0-0:18, 1-1:17, 0-1:12, 2-2:12, 0-2:7, 0-3:6, 1-0:6, 3-3:5, 2-1:5 |
| strong_home_fav | medium_control | 274 | preferred | 42.3 | 67.5 | 54.0 | 63.1 | 26.6 | 2.87 | 1-1:50, 2-2:24, 2-1:24, 1-2:21, 2-0:20, 1-0:18, 0-1:16, 0-0:15, 3-1:14, 3-0:11 |
| strong_home_fav | high_control | 1121 | preferred | 66.7 | 65.7 | 57.7 | 55.1 | 42.6 | 3.01 | 1-0:140, 2-1:137, 2-0:119, 1-1:110, 3-0:82, 3-1:71, 2-2:51, 0-1:45, 3-2:43, 0-0:42 |
| medium_home_fav | low_control | 483 | preferred | 35.8 | 68.1 | 54.0 | 61.9 | 23.6 | 2.86 | 1-1:74, 1-2:43, 0-0:39, 2-1:38, 2-2:37, 1-0:32, 0-1:31, 2-0:29, 3-1:20, 2-3:18 |
| medium_home_fav | medium_control | 689 | preferred | 38.8 | 69.2 | 51.7 | 62.6 | 24.7 | 2.76 | 1-1:126, 2-1:64, 0-0:53, 2-2:52, 1-2:47, 1-0:47, 0-1:44, 2-0:41, 3-1:34, 0-2:22 |
| medium_home_fav | high_control | 704 | preferred | 62.8 | 70.2 | 54.8 | 54.4 | 43.8 | 2.86 | 1-0:106, 2-1:88, 2-0:72, 1-1:65, 1-2:42, 3-0:42, 0-0:37, 3-1:36, 2-2:32, 3-2:27 |

## Main H2 Table: Away Favorite Strength x Control
| away_fav_bucket | control_bucket | N | Sample | Away win % | Under 3.5 % | Over 2.5 % | BTTS % | Fav win + O2.5 % | Avg goals | Top scores |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| very_strong_away_fav | low_control | 11 | ignore (<50) | 0.0 | 90.9 | 18.2 | 81.8 | 0.0 | 2.0 | 1-1:7, 2-1:1, 2-2:1, 0-0:1, 1-0:1 |
| very_strong_away_fav | medium_control | 48 | ignore (<50) | 10.4 | 62.5 | 43.8 | 81.2 | 8.3 | 2.75 | 1-1:19, 2-2:11, 1-0:4, 0-0:3, 3-2:2, 1-3:2, 3-1:1, 1-2:1, 3-3:1, 2-1:1 |
| very_strong_away_fav | high_control | 605 | preferred | 73.4 | 59.5 | 64.6 | 54.7 | 51.6 | 3.2 | 1-2:78, 0-1:71, 0-2:61, 1-3:49, 0-3:45, 1-1:35, 1-4:27, 2-2:27, 2-3:26, 0-4:23 |
| strong_away_fav | low_control | 117 | preferred | 22.2 | 68.4 | 47.9 | 63.2 | 15.4 | 2.74 | 1-1:25, 0-0:13, 2-1:9, 1-0:8, 2-2:7, 2-0:7, 3-1:6, 1-2:5, 1-3:4, 0-2:4 |
| strong_away_fav | medium_control | 255 | preferred | 25.9 | 71.0 | 52.9 | 62.7 | 18.0 | 2.74 | 1-1:48, 2-1:32, 2-2:26, 1-0:21, 0-0:21, 0-1:14, 1-2:11, 2-0:10, 0-3:10, 3-1:9 |
| strong_away_fav | high_control | 676 | preferred | 63.0 | 66.0 | 58.6 | 53.0 | 40.8 | 2.96 | 1-2:85, 0-1:79, 0-2:71, 1-1:45, 0-3:42, 0-0:36, 2-2:34, 1-0:34, 2-1:33, 1-4:30 |
| medium_away_fav | low_control | 309 | preferred | 21.0 | 73.8 | 47.2 | 57.6 | 12.0 | 2.56 | 1-1:55, 2-1:31, 0-0:29, 1-0:27, 2-0:24, 2-2:23, 0-1:18, 1-2:15, 3-1:14, 3-0:13 |
| medium_away_fav | medium_control | 399 | preferred | 32.8 | 69.2 | 52.1 | 58.4 | 20.8 | 2.71 | 1-1:59, 2-2:38, 2-1:33, 0-0:32, 1-0:30, 0-1:27, 1-2:25, 2-0:22, 0-2:21, 3-1:15 |
| medium_away_fav | high_control | 275 | preferred | 74.5 | 69.5 | 57.1 | 52.7 | 46.9 | 2.89 | 0-1:43, 1-2:43, 0-2:33, 2-3:22, 0-3:20, 1-1:19, 1-3:16, 1-0:11, 1-4:9, 0-0:9 |

## Chaos Effect Table
| pattern | chaos_bucket | N | Sample | Over 2.5 % | Under 3.5 % | BTTS % | Upset % | Draw % | Avg goals | Top scores |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1_strong_home_high_control | low_chaos | 1530 | preferred | 60.1 | 61.9 | 52.0 | 10.3 | 17.6 | 3.12 | 1-0:184, 2-0:177, 2-1:169, 1-1:123, 3-0:120, 3-1:109, 4-0:79, 0-0:65, 2-2:61, 3-2:60 |
| H1_strong_home_high_control | medium_chaos | 825 | preferred | 61.0 | 63.3 | 51.9 | 11.6 | 17.1 | 3.15 | 2-1:95, 1-0:89, 2-0:89, 3-0:77, 1-1:70, 3-1:55, 0-1:34, 4-1:34, 2-2:33, 4-0:32 |
| H2_strong_away_high_control | low_chaos | 794 | preferred | 61.2 | 64.0 | 54.2 | 13.2 | 17.4 | 3.07 | 1-2:108, 0-1:97, 0-2:83, 0-3:63, 1-1:58, 1-3:44, 2-3:37, 1-4:37, 0-0:35, 2-2:32 |
| H2_strong_away_high_control | medium_chaos | 487 | preferred | 61.8 | 61.2 | 53.2 | 18.7 | 15.8 | 3.08 | 1-2:55, 0-1:53, 0-2:49, 1-3:32, 2-1:30, 2-2:29, 1-0:25, 0-0:24, 0-3:24, 1-1:22 |

## League Split
| pattern | league_display | N | Sample | Favorite win % | Under 3.5 % | Over 2.5 % | BTTS % | Fav win + U3.5 % | Fav win + O2.5 % | Avg goals |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1_strong_home_high_control | Bundesliga | 269 | preferred | 68.0 | 59.9 | 63.6 | 53.2 | 36.4 | 50.2 | 3.23 |
| H1_strong_home_high_control | D2 | 183 | preferred | 82.5 | 61.7 | 66.1 | 49.2 | 51.9 | 56.8 | 3.33 |
| H1_strong_home_high_control | Eredivisie | 328 | preferred | 78.0 | 56.1 | 65.5 | 51.8 | 40.2 | 56.7 | 3.36 |
| H1_strong_home_high_control | La Liga | 332 | preferred | 70.5 | 69.9 | 53.0 | 45.8 | 47.6 | 43.7 | 2.81 |
| H1_strong_home_high_control | Ligue 1 | 298 | preferred | 66.1 | 62.4 | 60.1 | 55.7 | 37.2 | 47.3 | 3.08 |
| H1_strong_home_high_control | MLS | 270 | preferred | 78.5 | 58.9 | 68.1 | 58.1 | 44.8 | 57.8 | 3.38 |
| H1_strong_home_high_control | Premier League | 346 | preferred | 70.5 | 59.0 | 60.7 | 54.9 | 39.3 | 47.4 | 3.2 |
| H1_strong_home_high_control | Serie A | 329 | preferred | 65.3 | 69.9 | 50.8 | 47.1 | 45.3 | 37.1 | 2.81 |
| H2_strong_away_high_control | Bundesliga | 147 | preferred | 66.0 | 57.8 | 67.3 | 60.5 | 36.7 | 48.3 | 3.41 |
| H2_strong_away_high_control | D2 | 120 | preferred | 69.2 | 66.7 | 58.3 | 47.5 | 45.0 | 45.0 | 2.93 |
| H2_strong_away_high_control | Eredivisie | 224 | preferred | 78.1 | 55.8 | 68.3 | 55.8 | 41.5 | 57.1 | 3.38 |
| H2_strong_away_high_control | La Liga | 153 | preferred | 62.1 | 71.9 | 51.6 | 47.7 | 44.4 | 35.9 | 2.63 |
| H2_strong_away_high_control | Ligue 1 | 167 | preferred | 61.7 | 67.1 | 56.9 | 55.1 | 40.1 | 40.7 | 2.87 |
| H2_strong_away_high_control | Premier League | 218 | preferred | 67.4 | 59.6 | 61.5 | 48.2 | 37.6 | 45.4 | 3.11 |
| H2_strong_away_high_control | Serie A | 223 | preferred | 67.7 | 67.3 | 61.4 | 57.0 | 46.2 | 44.8 | 2.99 |

## Season Split
| pattern | season | N | Sample | Favorite win % | Under 3.5 % | Over 2.5 % | BTTS % | Fav win + U3.5 % | Fav win + O2.5 % | Avg goals |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1_strong_home_high_control | 2021.0 | 597 | preferred | 71.9 | 64.2 | 58.1 | 49.7 | 42.2 | 48.4 | 3.05 |
| H1_strong_home_high_control | 2022.0 | 657 | preferred | 72.1 | 63.8 | 60.6 | 51.6 | 43.5 | 49.9 | 3.12 |
| H1_strong_home_high_control | 2023.0 | 746 | preferred | 72.1 | 61.9 | 60.1 | 51.2 | 43.3 | 48.1 | 3.1 |
| H1_strong_home_high_control | 2024.0 | 242 | preferred | 74.4 | 56.6 | 64.5 | 55.4 | 39.7 | 51.7 | 3.5 |
| H1_strong_home_high_control | 2025.0 | 113 | preferred | 62.8 | 60.2 | 65.5 | 62.8 | 38.1 | 46.0 | 3.16 |
| H2_strong_away_high_control | 2021.0 | 382 | preferred | 70.4 | 60.7 | 64.4 | 57.1 | 39.3 | 51.6 | 3.15 |
| H2_strong_away_high_control | 2022.0 | 386 | preferred | 71.0 | 68.1 | 58.5 | 48.7 | 48.2 | 43.5 | 2.94 |
| H2_strong_away_high_control | 2023.0 | 393 | preferred | 65.9 | 60.3 | 62.1 | 53.9 | 38.7 | 45.5 | 3.15 |
| H2_strong_away_high_control | 2024.0 | 98 | small sample | 57.1 | 66.3 | 57.1 | 55.1 | 38.8 | 36.7 | 2.92 |

## Stability Detail: H1 Strong Home Favorites by Season
| control_bucket | season | N | home_win_under35 | Under 3.5 % | Over 2.5 % | BTTS % | Fav win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low_control | 2023.0 | 57 | 7.0 | 68.4 | 57.9 | 61.4 | 8.8 |
| medium_control | 2021.0 | 57 | 8.8 | 68.4 | 52.6 | 73.7 | 10.5 |
| medium_control | 2022.0 | 52 | 13.5 | 71.2 | 40.4 | 69.2 | 19.2 |
| medium_control | 2023.0 | 83 | 30.1 | 67.5 | 56.6 | 59.0 | 48.2 |
| medium_control | 2024.0 | 86 | 29.1 | 65.1 | 54.7 | 62.8 | 50.0 |
| high_control | 2021.0 | 597 | 42.2 | 64.2 | 58.1 | 49.7 | 71.9 |
| high_control | 2022.0 | 657 | 43.5 | 63.8 | 60.6 | 51.6 | 72.1 |
| high_control | 2023.0 | 746 | 43.3 | 61.9 | 60.1 | 51.2 | 72.1 |
| high_control | 2024.0 | 242 | 39.7 | 56.6 | 64.5 | 55.4 | 74.4 |
| high_control | 2025.0 | 113 | 38.1 | 60.2 | 65.5 | 62.8 | 62.8 |

## Stability Detail: H2 Strong Away Favorites by Season
| control_bucket | season | N | away_win_over25 | Under 3.5 % | Over 2.5 % | BTTS % | Fav win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| medium_control | 2021.0 | 73 | 4.1 | 79.5 | 43.8 | 67.1 | 6.8 |
| medium_control | 2022.0 | 83 | 1.2 | 77.1 | 39.8 | 57.8 | 8.4 |
| medium_control | 2023.0 | 106 | 30.2 | 59.4 | 62.3 | 68.9 | 39.6 |
| high_control | 2021.0 | 382 | 51.6 | 60.7 | 64.4 | 57.1 | 70.4 |
| high_control | 2022.0 | 386 | 43.5 | 68.1 | 58.5 | 48.7 | 71.0 |
| high_control | 2023.0 | 393 | 45.5 | 60.3 | 62.1 | 53.9 | 65.9 |
| high_control | 2024.0 | 98 | 36.7 | 66.3 | 57.1 | 55.1 | 57.1 |

## Specific Questions
1. High-control strong home favorites vs low-control strong home favorites, Under 3.5 delta: **-9.7 pp**.
2. High-control strong home favorites home-win delta: **54.9 pp**.
3. High-control strong home favorites Home Win + Under 3.5 delta: **32.1 pp**.
4. High-control strong away favorites Over 2.5 minus high-control strong home favorites Over 2.5: **1.0 pp**.
5. High-control strong away favorites Away Win + Over 2.5 rate: **45.9%**.
6. High chaos vs low chaos deltas: Over 2.5 **-11.3 pp**, BTTS **6.3 pp**, draw **17.7 pp**, upset **20.4 pp**.
7. Control score is most directly useful as a 1X2 confidence indicator; goal-profile usefulness is secondary and must be checked by favorite side.
8. Chaos score is more useful as a volatility / prediction-risk indicator than as a standalone goal-heavy detector unless paired with favorite side and scoring-form context.

## Clear Answers
- a) Is H1 supported? **Not clearly** under the sample and repeatability constraints.
- b) Is H2 supported? **Yes, directionally** under the sample and repeatability constraints.
- c) Is high chaos useful? **Yes, as a volatility warning**.
- d) Strongest pattern: choose the largest repeatable delta from the H1/H2 and chaos tables above with N >= 100 and at least two seasons.
- e) Observation-only pattern: any row marked small sample, one-league-only, or one-season-only should remain observation-only.

No betting recommendation. No ROI claim because exact market odds for these derived goal-pattern markets are not present.