# v2.0 Historical Internet Prediction Engine

This block exists to connect existing source modules into one historical as-of prediction workflow instead of creating parallel mini systems.

As-of means the engine only uses records available before the analysis cutoff. A matchday 5 analysis must not use matchday 30 data.

Sources:
- football-data results for table and form
- Understat-style xG and player xG/xA
- historical odds snapshots
- future API-Football / The Odds API adapters can be added behind explicit network and API-key gates

Network mode is disabled by default. Cache and rate-limit rules are part of `config/v20_internet_sources.yaml`.

The model combines market priors, historical form, xG structure and data-quality risk. Outputs are `MODEL_TIP`, `ANALYST_LEAN`, `NO_BET`, or `DATA_BLOCKED`.

No stake, ROI, money management or automatic betting is included.

Run:

```powershell
$PY scripts\run_v20_historical_internet_prediction.py --home-team "Demo Home" --away-team "Demo Away" --competition "Demo League" --season "2025/26" --match-date 2026-02-14 --cutoff-policy MATCH_DATE_START --mock-data-dir tests\fixtures\v20_historical_internet_prediction --source-profile config\v20_internet_sources.yaml --output-dir outputs\analysis_preview\v20_historical_internet_prediction_demo --emit-all
```
