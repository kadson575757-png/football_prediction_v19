# v2.0.1 Understat xG Repair

The Understat live adapter supports plain JSON and embedded league-page `datesData` payloads. It writes raw payload, normalized matches, adapter diagnostics, cache metadata and xG as-of outputs.

If Understat is unavailable, the adapter returns `FAILED_FETCH` without crashing. If the HTML payload changes, it returns `FAILED_PARSE` with a clear recommended fix.
