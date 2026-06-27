from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_live_source_orchestrator import run_v20_live_source_orchestrator


def test_live_source_orchestrator_ready_partial_blocked(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    ready = run_v20_live_source_orchestrator(ctx, tmp_path / "ready", local_fallback_dir="tests/fixtures/v20_live_source_adapters", cache_dir=tmp_path / "cache")
    assert ready["live_source_status"] == "LIVE_SOURCES_READY"
    assert ready["football_data_available"] is True
    assert ready["xg_available"] is True
    assert ready["odds_available"] is True

    blocked = run_v20_live_source_orchestrator(ctx, tmp_path / "blocked", cache_only=True, cache_dir=tmp_path / "empty_cache")
    assert blocked["live_source_status"] == "LIVE_SOURCES_BLOCKED"
    assert (tmp_path / "blocked" / "live_source_coverage_matrix.csv").exists()
