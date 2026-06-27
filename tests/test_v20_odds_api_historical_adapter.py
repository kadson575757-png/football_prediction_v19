from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_odds_api_historical_adapter import run_odds_api_historical_adapter
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


FIXTURES = "tests/fixtures/v20_live_source_adapters"


def test_odds_api_missing_key_disables_source_without_secret(monkeypatch, tmp_path):
    monkeypatch.delenv("THE_ODDS_API_KEY", raising=False)
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    result = run_odds_api_historical_adapter(resolve_source_league("Demo League", "2025/26"), ctx, tmp_path)
    assert result["odds_api_status"] == "DISABLED_MISSING_KEY"
    assert "super_private" not in (tmp_path / "odds_api_result.json").read_text(encoding="utf-8")


def test_odds_api_mock_response_normalized_and_match_resolved(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    result = run_odds_api_historical_adapter(resolve_source_league("Demo League", "2025/26"), ctx, tmp_path, mock_json_path=f"{FIXTURES}/odds_api_historical_mock.json", cache_dir=tmp_path / "cache")
    assert result["odds_api_status"] == "SUCCESS"
    assert result["odds_1x2_available"] is True
    assert result["odds_totals_available"] is True
