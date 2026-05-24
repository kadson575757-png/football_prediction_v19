# Betting Backtest Report

## Summary

- Total matches: 56
- Total bets: 24
- No-bet count: 32
- Hit rate: 70.83%
- Total profit: 11.37 units
- ROI: 47.38%
- Yield: 47.38%
- Average edge: 10.81%

## Calibration

- Brier score: 0.5889
- Log loss: 0.9858
- Average predicted probability for winning picks: 39.74%
- No overconfidence warning.

## Performance By Pick Type

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Away | 2 | 1.14 | 57.00% | 50.00% |
| Home | 22 | 10.23 | 46.50% | 72.73% |

## Performance By League

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Unknown | 24 | 11.37 | 47.38% | 70.83% |

## Biggest Winning Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2023-09-19 | Arsenal vs Chelsea | Away | 3.14 | 2.14 |
| 2023-09-06 | Manchester Utd vs Arsenal | Home | 2.66 | 1.66 |
| 2023-08-22 | Chelsea vs Brighton | Home | 2.16 | 1.16 |
| 2023-08-19 | Brighton vs West Ham | Home | 2.12 | 1.12 |
| 2023-09-09 | Arsenal vs Manchester Utd | Home | 2.12 | 1.12 |

## Biggest Losing Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2023-08-10 | Arsenal vs West Ham | Home | 1.82 | -1.00 |
| 2023-09-06 | Liverpool vs Arsenal | Home | 2.26 | -1.00 |
| 2023-08-28 | Everton vs West Ham | Away | 2.69 | -1.00 |
| 2023-08-26 | Liverpool vs Brighton | Home | 1.93 | -1.00 |
| 2023-09-14 | Liverpool vs Manchester Utd | Home | 2.04 | -1.00 |

## Most Common No-Bet Reasons

| Reason | Count |
|---|---:|
| 1X2 hard tip locked: control model below 7/10 | 30 |
| No value bet: control score below 7 | 30 |
| Away-favorite degradation: home formation xG90 >= 1.20 | 19 |
| Over 1.5 not recommended: xG total proxy below threshold | 11 |
| No primary betting recommendation cleared all v1.9 gates | 5 |
| DNB locked: prob_edge_vs_opponent, control_ok, not_away_degradation | 5 |
| DNB locked: prob_edge_vs_opponent, control_ok, not_away_degradation, xg_edge_positive | 3 |
| No away value bet: away-favorite degradation triggered | 3 |
| DNB locked: control_ok, xg_edge_positive | 3 |
| DNB locked: prob_edge_vs_opponent, chaos_ok, control_ok, not_away_degradation | 2 |

> Backtests are diagnostics, not guarantees. Future matches can behave differently.