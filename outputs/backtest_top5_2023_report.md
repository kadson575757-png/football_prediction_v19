# Betting Backtest Report

## Summary

- Total matches: 1745
- Total bets: 840
- No-bet count: 905
- Hit rate: 44.05%
- Total profit: -62.10 units
- ROI: -7.39%
- Yield: -7.39%
- Average edge: 6.02%

## Calibration

- Brier score: 0.5726
- Log loss: 0.9627
- Average predicted probability for winning picks: 42.57%
- No overconfidence warning.

## Performance By Pick Type

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Away | 77 | -2.43 | -3.16% | 40.26% |
| Draw | 134 | 8.96 | 6.69% | 23.13% |
| Home | 629 | -68.63 | -10.91% | 48.97% |

## Performance By League

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Bundesliga | 159 | -16.98 | -10.68% | 38.99% |
| La Liga | 188 | 9.44 | 5.02% | 53.19% |
| Ligue 1 | 131 | -21.23 | -16.21% | 38.93% |
| Premier League | 191 | -25.49 | -13.35% | 43.46% |
| Serie A | 171 | -7.84 | -4.58% | 43.27% |

## Biggest Winning Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2023-12-09 | Ein Frankfurt vs Bayern Munich | Home | 9.00 | 8.00 |
| 2024-04-14 | Inter vs Cagliari | Draw | 8.00 | 7.00 |
| 2024-02-18 | Bochum vs Bayern Munich | Home | 8.00 | 7.00 |
| 2024-04-24 | Everton vs Liverpool | Home | 7.00 | 6.00 |
| 2023-12-03 | Man City vs Tottenham Hotspur | Draw | 6.00 | 5.00 |

## Biggest Losing Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2024-04-20 | FC Koln vs Darmstadt | Draw | 4.75 | -1.00 |
| 2023-08-13 | Brentford vs Tottenham Hotspur | Home | 2.75 | -1.00 |
| 2024-04-24 | Lorient vs Paris SG | Home | 7.50 | -1.00 |
| 2024-05-20 | Bologna vs Juventus | Home | 2.45 | -1.00 |
| 2024-02-25 | Dortmund vs Hoffenheim | Home | 1.50 | -1.00 |

## Most Common No-Bet Reasons

| Reason | Count |
|---|---:|
| xG unavailable; xG gates skipped | 1745 |
| 1X2 hard tip locked: control model below 7/10 | 580 |
| No value bet: control score below 7 | 580 |
| No value bet: best model edge below 3.00% | 499 |
| No primary betting recommendation cleared all v1.9 gates | 442 |
| DNB locked: control_ok | 191 |
| DNB locked: prob_edge_vs_opponent, control_ok | 111 |
| Kellerduell / both teams TDI >= 2: Over 1.5 locked | 71 |
| DNB locked: side_tdi_ok, control_ok | 63 |
| DNB locked: side_tdi_ok | 30 |

> Backtests are diagnostics, not guarantees. Future matches can behave differently.