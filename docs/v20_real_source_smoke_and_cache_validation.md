# v2.0 Real Source Smoke and Cache Validation

Real source smoke is manual and only uses network when `--enable-network` is supplied. Cache validation runs offline and reports READY, PARTIAL, or BLOCKED without crashing.

No tests perform real network calls.
