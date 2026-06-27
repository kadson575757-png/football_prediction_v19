# v2.0.1 No-Odds Policy

The Odds API key is optional. Missing odds are a source-quality penalty and must not alone produce `DATA_BLOCKED`.

Hard blockers remain fixture resolution failure, missing table/form data, leakage/as-of failure, and unsupported core sources.

Without odds, `MODEL_TIP` is allowed only when fixture, table/form, xG, leakage and model confidence are strong. Otherwise the decision must be `ANALYST_LEAN` or `NO_BET`.

No automatic betting, staking, ROI, profit or money-management output is enabled.
