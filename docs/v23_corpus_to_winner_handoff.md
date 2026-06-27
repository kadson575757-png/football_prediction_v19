# v2.3 Corpus-to-Winner Handoff

v2.2 built the real multi-league corpus and coverage layer. v2.3 connects that corpus to the winner feature store without forcing every match through live resolver/as-of rebuilds.

For corpus-backed backtests, completed football-data rows produce as-of form features from previous corpus matches. Early-season rows are marked as `early_season_risk` and capped in confidence rather than hard blocked.

Missing xG and missing odds are non-blocking for results-only rows. They lower source quality, add risk notes, and route the model through `TIER_2_RESULTS_ONLY`.

An all-DATA_BLOCKED backtest is treated as a blocking bug, not a ready release signal.

No automatic betting, no staking, no ROI.
