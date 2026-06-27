# v2.3 DATA_BLOCKED Policy

`DATA_BLOCKED` is reserved for hard data failures:

- fixture missing or ambiguous
- missing result for backtest evaluation
- missing table/form core source
- leakage guard failure
- unsupported league
- corrupt corpus row
- no core source available

Non-hard missing data must not create `DATA_BLOCKED` by itself:

- missing xG
- missing odds
- missing lineups
- missing injuries
- Understat parse failure
- odds match not found

These non-hard issues are surfaced as missing data, risk notes, confidence caps, and partial-model diagnostics.
