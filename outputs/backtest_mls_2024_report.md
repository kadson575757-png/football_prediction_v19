# Betting Backtest Report

## Summary

- Total matches: 1061
- Total bets: 195
- No-bet count: 866
- Hit rate: 18.97%
- Total profit: -22.19 units
- ROI: -11.38%
- Yield: -11.38%
- Average edge: 7.21%

## Calibration

- Brier score: 0.6335
- Log loss: 1.0512
- Average predicted probability for winning picks: 36.02%
- Warning: high-confidence picks look overconfident. Avg confidence 62.76%, hit rate 52.00%.

## Performance By Pick Type

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Away | 65 | 0.46 | 0.71% | 21.54% |
| Draw | 128 | -20.65 | -16.13% | 17.97% |
| Home | 2 | -2.00 | -100.00% | 0.00% |

## Performance By League

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| MLS | 195 | -22.19 | -11.38% | 18.97% |

## Biggest Winning Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2024-08-24 | Real Salt Lake vs San Jose Earthquakes | Away | 8.00 | 7.00 |
| 2025-05-31 | FC Cincinnati vs DC United | Away | 7.00 | 6.00 |
| 2025-09-27 | Charlotte FC vs CF Montreal | Away | 6.50 | 5.50 |
| 2024-08-24 | Houston Dynamo vs Toronto FC | Away | 6.00 | 5.00 |
| 2025-09-13 | Seattle Sounders vs LA Galaxy | Draw | 5.75 | 4.75 |

## Biggest Losing Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2024-02-24 | Columbus Crew vs Atlanta United | Away | 4.55 | -1.00 |
| 2024-02-24 | Los Angeles FC vs Seattle Sounders | Away | 5.00 | -1.00 |
| 2024-02-24 | Orlando City vs CF Montreal | Away | 5.40 | -1.00 |
| 2024-02-25 | Nashville SC vs New York Red Bulls | Away | 2.72 | -1.00 |
| 2024-02-25 | FC Cincinnati vs Toronto FC | Away | 4.75 | -1.00 |

## Most Common No-Bet Reasons

| Reason | Count |
|---|---:|
| xG unavailable; xG gates skipped | 1061 |
| 1X2 hard tip locked: control model below 7/10 | 846 |
| No value bet: control score below 7 | 846 |
| No primary betting recommendation cleared all v1.9 gates | 786 |
| DNB locked: control_ok | 338 |
| DNB locked: prob_edge_vs_opponent, control_ok | 312 |
| No value bet: best model edge below 3.00% | 50 |
| DNB locked: prob_edge_vs_opponent, chaos_ok, control_ok | 30 |
| DNB locked: chaos_ok, control_ok | 29 |
| Kellerduell / both teams TDI >= 2: Over 1.5 locked | 27 |

> Backtests are diagnostics, not guarantees. Future matches can behave differently.