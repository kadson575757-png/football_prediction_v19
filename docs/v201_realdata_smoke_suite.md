# v2.0.1 Realdata Smoke Suite

`scripts/run_v20_realdata_smoke_suite.py` runs a small multi-league realdata preview cohort through fixture, football-data, Understat/xG, optional odds, leakage, model and decision layers.

The suite reports `MODEL_TIP`, `ANALYST_LEAN`, `NO_BET` and `DATA_BLOCKED` counts. Odds missing because no API key was provided is tracked as coverage, not a betting metric.
