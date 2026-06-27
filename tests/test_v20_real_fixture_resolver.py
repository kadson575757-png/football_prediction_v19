from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_real_fixture_resolver import resolve_real_fixture


def test_real_fixture_resolver_resolved_partial_not_found(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-14"))
    paths = {"football": "tests/fixtures/v20_real_match_autopilot/football_data_live_mock.csv", "xg": "tests/fixtures/v20_real_match_autopilot/understat_league_mock.json"}
    partial = resolve_real_fixture(ctx, paths, tmp_path)
    assert partial.fixture_resolution_status == "PARTIAL"
    missing = resolve_real_fixture(resolve_analysis_cutoff(build_match_context("X", "Y", "Demo League", "2025/26", "2026-02-14")), paths)
    assert missing.fixture_resolution_status == "NOT_FOUND"
