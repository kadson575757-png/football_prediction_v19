# Betting Backtest Report

## Summary

- Total matches: 304
- Total bets: 143
- No-bet count: 161
- Hit rate: 30.07%
- Total profit: 26.76 units
- ROI: 18.71%
- Yield: 18.71%
- Average edge: 10.23%

## Calibration

- Brier score: 0.5922
- Log loss: 0.9868
- Average predicted probability for winning picks: 39.58%
- No overconfidence warning.

## Performance By Pick Type

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Away | 16 | -2.75 | -17.19% | 12.50% |
| Draw | 89 | 27.71 | 31.13% | 28.09% |
| Home | 38 | 1.80 | 4.74% | 42.11% |

## Performance By League

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Unknown | 143 | 26.76 | 18.71% | 30.07% |

## Biggest Winning Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2024-02-18 | Bochum vs Bayern Munich | Home | 8.00 | 7.00 |
| 2024-01-13 | RB Leipzig vs Ein Frankfurt | Away | 7.50 | 6.50 |
| 2023-09-01 | Dortmund vs Heidenheim | Draw | 7.00 | 6.00 |
| 2024-05-11 | RB Leipzig vs Werder Bremen | Draw | 6.50 | 5.50 |
| 2023-10-07 | RB Leipzig vs Bochum | Draw | 6.00 | 5.00 |

## Biggest Losing Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2023-08-18 | Werder Bremen vs Bayern Munich | Home | 7.50 | -1.00 |
| 2023-08-19 | Stuttgart vs Bochum | Draw | 4.33 | -1.00 |
| 2023-08-19 | Dortmund vs FC Koln | Draw | 5.00 | -1.00 |
| 2023-08-25 | RB Leipzig vs Stuttgart | Away | 5.75 | -1.00 |
| 2023-08-27 | Bayern Munich vs Augsburg | Draw | 12.00 | -1.00 |

## Most Common No-Bet Reasons

| Reason | Count |
|---|---:|
| DNB locked: xg_edge_positive | 174 |
| No primary betting recommendation cleared all v1.9 gates | 147 |
| 1X2 hard tip locked: control model below 7/10 | 146 |
| No value bet: control score below 7 | 146 |
| DNB locked: xg_edge_positive, control_ok | 47 |
| DNB locked: prob_edge_vs_opponent, xg_edge_positive, control_ok | 37 |
| No value bet: best model edge below 3.00% | 34 |
| DNB locked: xg_edge_positive, side_tdi_ok, control_ok | 19 |
| Kellerduell / both teams TDI >= 2: Over 1.5 locked | 13 |
| DNB locked: prob_edge_vs_opponent, xg_edge_positive, side_tdi_ok, chaos_ok, control_ok | 6 |

> Backtests are diagnostics, not guarantees. Future matches can behave differently.