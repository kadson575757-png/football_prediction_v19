from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_final_historical_analyst_report import write_final_historical_analyst_report
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context


def test_live_source_report_shows_source_status_cache_and_safety(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    path = write_final_historical_analyst_report(
        ctx,
        {"leakage_status": "CLEAN"},
        {"table_available": True, "xg_available": True, "odds_1x2_available": False},
        {"lineups_available": False, "injuries_available": False},
        {"model_status": "MODEL_PARTIAL", "home_win_probability": 0.4, "draw_probability": 0.3, "away_win_probability": 0.3},
        {"decision_class": "NO_BET", "primary_tip": "NO_BET", "no_bet_reasons": "odds missing"},
        tmp_path,
        live_sources={"live_source_status": "LIVE_SOURCES_PARTIAL", "cache_used": True, "football": {"football_data_live_status": "CACHE_HIT"}, "xg": {"understat_live_status": "CACHE_HIT"}, "odds": {"odds_api_status": "DISABLED_MISSING_KEY"}, "api_football": {"api_football_optional_status": "DISABLED_BY_CONFIG"}},
    )
    text = open(path, encoding="utf-8").read()
    assert "Live Sources Used" in text
    assert "Cache Status" in text
    assert "API Key Presence" in text
    assert "No automatic betting. No stake. No ROI." in text
