from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


FIXTURES = "tests/fixtures/v20_live_source_adapters"


def test_football_data_live_adapter_normalizes_mock_and_excludes_future(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    mapping = resolve_source_league("Demo League", "2025/26")
    result = run_football_data_live_adapter(mapping, ctx, tmp_path, mock_csv_path=f"{FIXTURES}/football_data_live_mock.csv", cache_dir=tmp_path / "cache")
    assert result["football_data_live_status"] == "SUCCESS"
    assert result["table_available"] is True
    assert result["matches_used"] == 3


def test_football_data_live_adapter_cache_hit_and_network_disabled(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    mapping = resolve_source_league("Demo League", "2025/26")
    run_football_data_live_adapter(mapping, ctx, tmp_path, mock_csv_path=f"{FIXTURES}/football_data_live_mock.csv", cache_dir=tmp_path / "cache")
    cached = run_football_data_live_adapter(mapping, ctx, tmp_path, cache_dir=tmp_path / "cache")
    assert cached["football_data_live_status"] == "CACHE_HIT"
    disabled = run_football_data_live_adapter(mapping, ctx, tmp_path / "disabled", cache_dir=tmp_path / "empty_cache")
    assert disabled["football_data_live_status"] == "DISABLED_NETWORK"
