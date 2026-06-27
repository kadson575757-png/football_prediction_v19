# v2.0.1 Realdata Acceptance Checklist

- football-data live/cache works.
- Understat parser/cache works or fails with clear diagnostics.
- Odds API key is optional.
- Missing odds alone do not create `DATA_BLOCKED`.
- Fixture search returns candidates and recommended run commands.
- Smoke suite and cache-only repeat exist.
- No-leakage backtest reports non-betting metrics only.
- Network calls are off by default and live mode requires `--enable-network`.
- No automatic betting, staking or ROI output is enabled.
