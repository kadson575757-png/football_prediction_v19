import json

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v20_understat_live_adapter import run_understat_live_adapter


def test_understat_cache_only_repeat(tmp_path):
    payload = tmp_path / "understat.json"
    payload.write_text(json.dumps({"matches": [{"date": "2025-08-10", "home_team": "Demo Home", "away_team": "Demo Away", "home_xg": 1.7, "away_xg": 0.9}]}), encoding="utf-8")
    context = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-15"))
    mapping = resolve_source_league("Demo League", "2025/26")
    cache = tmp_path / "cache"
    run_understat_live_adapter(mapping, context, tmp_path / "first", mock_json_path=payload, cache_dir=cache)
    second = run_understat_live_adapter(mapping, context, tmp_path / "second", cache_dir=cache)
    assert second["understat_live_status"] == "CACHE_HIT"
    assert second["xg_available"] is True
