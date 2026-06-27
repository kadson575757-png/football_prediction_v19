from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v20_understat_live_adapter import run_understat_live_adapter


FIXTURES = "tests/fixtures/v20_live_source_adapters"


def test_understat_live_adapter_normalizes_mock_xg_and_players(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    mapping = resolve_source_league("Demo League", "2025/26")
    result = run_understat_live_adapter(mapping, ctx, tmp_path, mock_json_path=f"{FIXTURES}/understat_league_mock.json", mock_players_json_path=f"{FIXTURES}/understat_players_mock.json", cache_dir=tmp_path / "cache")
    assert result["understat_live_status"] == "SUCCESS"
    assert result["xg_available"] is True
    assert result["player_xg_available"] is True


def test_understat_live_adapter_cache_disabled_and_unsupported(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Eredivisie", "2025/26", "2026-02-14"))
    mapping = resolve_source_league("Eredivisie", "2025/26")
    result = run_understat_live_adapter(mapping, ctx, tmp_path, cache_dir=tmp_path / "cache")
    assert result["understat_live_status"] == "UNSUPPORTED_LEAGUE"
