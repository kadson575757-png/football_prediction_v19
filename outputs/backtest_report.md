# Betting Backtest Report

## Summary

- Total matches: 275
- Total bets: 109
- No-bet count: 166
- Hit rate: 100.00%
- Total profit: 134.07 units
- ROI: 123.00%
- Yield: 123.00%
- Average edge: 23.46%

## Calibration

- Brier score: 0.2447
- Log loss: 0.5026
- Average predicted probability for winning picks: 61.14%
- No overconfidence warning.

## Performance By Pick Type

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Away | 13 | 15.86 | 122.00% | 100.00% |
| Draw | 10 | 25.83 | 258.30% | 100.00% |
| Home | 86 | 92.38 | 107.42% | 100.00% |

## Performance By League

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Unknown | 109 | 134.07 | 123.00% | 100.00% |

## Biggest Winning Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2021-09-06 | Manchester Utd vs Everton | Draw | 3.70 | 2.70 |
| 2021-08-14 | Liverpool vs Tottenham | Draw | 3.66 | 2.66 |
| 2021-08-26 | Tottenham vs West Ham | Draw | 3.64 | 2.64 |
| 2020-10-01 | Arsenal vs Tottenham | Draw | 3.61 | 2.61 |
| 2019-09-18 | Arsenal vs Manchester Utd | Draw | 3.59 | 2.59 |

## Biggest Losing Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2020-08-22 | Liverpool vs Everton | Home | 1.71 | 0.71 |
| 2021-09-11 | Liverpool vs Everton | Home | 1.71 | 0.71 |
| 2023-09-04 | Liverpool vs Everton | Home | 1.71 | 0.71 |
| 2022-09-21 | Liverpool vs Everton | Home | 1.71 | 0.71 |
| 2020-08-22 | Arsenal vs Everton | Home | 1.76 | 0.76 |

## Most Common No-Bet Reasons

| Reason | Count |
|---|---:|
| 1X2 hard tip locked: control model below 7/10 | 122 |
| No value bet: control score below 7 | 122 |
| Away-favorite degradation: home formation xG90 >= 1.20 | 114 |
| No away value bet: away-favorite degradation triggered | 63 |
| Over 1.5 not recommended: xG total proxy below threshold | 39 |
| DNB locked: not_away_degradation | 33 |
| DNB locked: xg_edge_positive | 30 |
| No primary betting recommendation cleared all v1.9 gates | 25 |
| DNB locked: not_away_degradation, xg_edge_positive | 23 |
| DNB locked: control_ok, not_away_degradation, xg_edge_positive | 20 |

> Backtests are diagnostics, not guarantees. Future matches can behave differently.