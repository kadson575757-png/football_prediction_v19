# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] - 2025-05-16

### Initial release

#### Supported workflows

| Workflow | Command(s) |
|---|---|
| Data download | `download-football-data`, `download-prepare-football-data` |
| Historical data preparation | `prepare-data`, `import-football-data`, `import-fbref`, `import-and-prepare` |
| xG import | `prepare-xg`, `merge-xg-history` |
| Odds import | `prepare-odds`, `merge-odds-fixtures` |
| Fixture preparation | `prepare-fixtures` |
| Model training | `train` |
| Model comparison + calibration | `compare-models` |
| Single prediction | `predict` |
| Fixture-list prediction | `predict-fixtures` |
| Value betting logic | built into `predict` / `predict-fixtures` |
| Backtesting | `backtest-bets` |
| Excel quality dashboard | `export-excel` |
| End-to-end pipeline | `run-pipeline` |
| Environment check | `doctor` |

#### Feature summary

- Rolling xG/xGA features, form windows, rest days, market odds features
- v1.9 rule overlay: control score, chaos score, TDI, DNB blocks,
  away-favorite degradation
- Value betting edge calculation and bet recommendation
- Probability calibration via isotonic regression (compare-models)
- Team name normalization via config/team_aliases.json
- FBref, Understat, football-data.co.uk, and native CSV format support
- Excel workbook with up to 12 sheets: predictions, value bets, model
  comparison, calibration, backtest summary, feature metadata

#### Known limitations

- xG matching uses team-name normalization; aliases must be configured
  if teams appear under multiple names
- Calibration requires at least 30 training rows and 2 classes
- The model comparison selects by log loss; other metrics are reported
  but not used for selection
