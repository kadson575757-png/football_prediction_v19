# Data schema

## Required historical match columns

| Column | Type | Meaning |
|---|---:|---|
| Date | date | Match date |
| Wk | int/float | Matchweek |
| Home | string | Home team |
| Away | string | Away team |
| xG | float | Home expected goals |
| xG.1 | float | Away expected goals |
| Score | string | Result, e.g. `2-1` or `2–1` |
| Venue | string | Stadium |
| Referee | string | Referee |

## Optional columns

| Column | Meaning |
|---|---|
| odds_home | closing decimal odds for home win |
| odds_draw | closing decimal odds for draw |
| odds_away | closing decimal odds for away win |
| odds_home_open, odds_draw_open, odds_away_open | opening odds for market movement |
| attendance | attendance |
| formation_home_xg90, formation_away_xg90 | manual tactical/formation xG90 signal |
| set_piece_xg_ratio_home, set_piece_xg_ratio_away | manual set-piece danger |
| fatigue_home, fatigue_away | manual fatigue modifier, 0-1 |

## Target labels

- `H` = Home win
- `D` = Draw
- `A` = Away win
