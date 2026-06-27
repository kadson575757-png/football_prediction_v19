# v2.0.1 Cache-Only Workflow

Live network access is disabled by default and only allowed with `--enable-network`.

After a successful live or fallback run writes cache files, repeat with `--cache-only` to reuse cached football-data and Understat payloads without another fetch.

Cache-only repeats must preserve safety flags: no automatic betting, no staking and no ROI.
