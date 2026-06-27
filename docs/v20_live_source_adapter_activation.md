# v2.0 Live Source Adapter Activation

This layer connects the historical internet prediction preview to live-source-ready adapters while keeping tests fully offline.

Modes:

- Mock mode uses local fixture CSV/JSON files.
- Cache-only mode uses cached source payloads only and never performs network calls.
- Live source mode is enabled only with `--enable-network`.

Sources:

- football-data.co.uk for historical results and available odds columns.
- Understat for cached/public xG payloads. Cache and rate limits are required.
- The Odds API for historical odds snapshots when `THE_ODDS_API_KEY` is present.
- API-Football is optional and prepared for future lineups/injuries.

PowerShell API key examples:

```powershell
$env:THE_ODDS_API_KEY="..."
$env:APIFOOTBALL_KEY="..."
```

Safety:

- No paywall, login, or captcha bypass.
- No aggressive requests.
- No stake, ROI, money management, or automatic betting.
- Missing sources degrade to partial coverage, analyst lean, no bet, or data blocked.

Troubleshooting:

- `DISABLED_NETWORK`: rerun with `--enable-network` or provide cache.
- `DISABLED_MISSING_KEY`: configure the relevant environment variable.
- `UNSUPPORTED_LEAGUE`: check the source league resolver mapping.
- `MATCH_NOT_FOUND`: source payload exists but the exact match was not resolved.
- `NO_BET`: coverage, confidence, or leakage policy prevents a production recommendation.
