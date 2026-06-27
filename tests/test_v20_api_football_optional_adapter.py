from football_prediction_v19.analysis.v20_api_football_optional_adapter import run_api_football_optional_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


def test_api_football_optional_disabled_missing_key_and_mock(tmp_path, monkeypatch):
    ctx = build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14")
    mapping = resolve_source_league("Demo League", "2025/26")
    assert run_api_football_optional_adapter(mapping, ctx, tmp_path)["api_football_optional_status"] == "DISABLED_BY_CONFIG"
    monkeypatch.delenv("APIFOOTBALL_KEY", raising=False)
    assert run_api_football_optional_adapter(mapping, ctx, tmp_path, enabled=True)["api_football_optional_status"] == "DISABLED_MISSING_KEY"
    mock = run_api_football_optional_adapter(mapping, ctx, tmp_path, enabled=True, mock_json_path="tests/fixtures/v20_live_source_adapters/api_football_fixture_mock.json")
    assert mock["api_football_optional_status"] == "SUCCESS"
    assert mock["lineups_available"] is True
    assert mock["injuries_available"] is True
