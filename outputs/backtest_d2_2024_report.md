# Betting Backtest Report

## Summary

- Total matches: 303
- Total bets: 95
- No-bet count: 208
- Hit rate: 28.42%
- Total profit: -10.19 units
- ROI: -10.73%
- Yield: -10.73%
- Average edge: 6.76%

## Calibration

- Brier score: 0.6467
- Log loss: 1.0706
- Average predicted probability for winning picks: 35.88%
- No overconfidence warning.

## Performance By Pick Type

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| Away | 59 | -23.99 | -40.66% | 23.73% |
| Draw | 34 | 10.20 | 30.00% | 32.35% |
| Home | 2 | 3.60 | 180.00% | 100.00% |

## Performance By League

| Group | Bets | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|
| 2. Bundesliga | 95 | -10.19 | -10.73% | 28.42% |

## Biggest Winning Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2025-04-27 | Hamburger SV vs Karlsruher SC | Away | 5.25 | 4.25 |
| 2024-11-03 | Hamburger SV vs 1. FC Nürnberg | Draw | 4.75 | 3.75 |
| 2024-09-01 | SC Paderborn 07 vs SSV Ulm 1846 | Draw | 4.50 | 3.50 |
| 2025-05-18 | Eintracht Braunschweig vs 1. FC Nürnberg | Away | 4.33 | 3.33 |
| 2025-05-18 | Karlsruher SC vs SC Paderborn 07 | Home | 4.20 | 3.20 |

## Biggest Losing Bets

| Date | Match | Pick | Odds | Profit |
|---|---|---|---:|---:|
| 2024-08-10 | 1. FC Nürnberg vs FC Schalke 04 | Away | 2.25 | -1.00 |
| 2024-08-11 | SC Paderborn 07 vs SV Darmstadt 98 | Draw | 3.90 | -1.00 |
| 2024-08-23 | Karlsruher SC vs SV Elversberg | Away | 5.00 | -1.00 |
| 2024-08-11 | Preußen Münster vs Hannover 96 | Away | 2.10 | -1.00 |
| 2024-09-14 | FC Koln vs 1. FC Magdeburg | Draw | 5.00 | -1.00 |

## Most Common No-Bet Reasons

| Reason | Count |
|---|---:|
| xG unavailable; xG gates skipped | 303 |
| 1X2 hard tip locked: control model below 7/10 | 180 |
| No value bet: control score below 7 | 180 |
| No primary betting recommendation cleared all v1.9 gates | 158 |
| DNB locked: control_ok | 77 |
| DNB locked: prob_edge_vs_opponent, control_ok | 54 |
| No value bet: best model edge below 3.00% | 50 |
| DNB locked: side_tdi_ok, control_ok | 13 |
| Kellerduell / both teams TDI >= 2: Over 1.5 locked | 10 |
| DNB locked: prob_edge_vs_opponent, chaos_ok, control_ok | 9 |

> Backtests are diagnostics, not guarantees. Future matches can behave differently.