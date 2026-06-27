import pandas as pd

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


def test_football_data_cache_only_repeat(tmp_path):
    csv = tmp_path / "football.csv"
    pd.DataFrame([{"Date": "2025-08-10", "HomeTeam": "Demo Home", "AwayTeam": "Demo Away", "FTHG": 2, "FTAG": 1, "FTR": "H"}]).to_csv(csv, index=False)
    context = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-15"))
    mapping = resolve_source_league("Demo League", "2025/26")
    cache = tmp_path / "cache"
    run_football_data_live_adapter(mapping, context, tmp_path / "first", mock_csv_path=csv, cache_dir=cache)
    second = run_football_data_live_adapter(mapping, context, tmp_path / "second", cache_dir=cache)
    assert second["football_data_live_status"] == "CACHE_HIT"
    assert second["table_available"] is True
