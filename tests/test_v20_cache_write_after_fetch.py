from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


def test_mock_live_fetch_writes_cache_and_cache_only_reads(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    mapping = resolve_source_league("Demo League", "2025/26")
    first = run_football_data_live_adapter(mapping, ctx, tmp_path / "first", mock_csv_path="tests/fixtures/v20_one_command_runner/football_data_live_mock.csv", cache_dir=tmp_path / "cache")
    assert first["cache_written"] is True
    assert first["cache_used"] is False
    second = run_football_data_live_adapter(mapping, ctx, tmp_path / "second", cache_dir=tmp_path / "cache")
    assert second["football_data_live_status"] == "CACHE_HIT"
    assert second["cache_used"] is True
    assert "api" not in second["cache_path"].lower()
