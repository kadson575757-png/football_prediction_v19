# v2.0.2 Real No-Odds Quality Completion

v2.0.2 finishes the no-odds quality path for real-data preview runs.

Rules:

- Odds API key is optional.
- Missing odds alone must not create `DATA_BLOCKED`.
- Missing odds alone must not force source quality to `LOW` when fixture, table/form, xG and leakage are clean.
- Missing xG remains a serious quality limitation and should normally lead to `NO_BET` or a weak analyst read.
- `MODEL_TIP` without odds requires medium/high source quality and a clear confidence edge.

Safety remains unchanged: no automatic betting, no stake, no ROI, no profit and no money management.
