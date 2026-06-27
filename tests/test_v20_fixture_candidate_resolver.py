from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_real_fixture_resolver import resolve_real_fixture


def test_fixture_candidate_resolver_wrong_date_and_suggestions(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo Home", "Demo Away", "Demo League", "2025/26", "2026-02-13"))
    result = resolve_real_fixture(ctx, {"football_data": "tests/fixtures/v20_one_command_runner/football_data_live_mock.csv"}, tmp_path)
    assert result.fixture_resolution_status == "PARTIAL"
    assert result.candidate_matches
    assert result.date_tolerance_match_found or result.season_team_pair_found


def test_fixture_candidate_resolver_similar_team_suggestions(tmp_path):
    ctx = resolve_analysis_cutoff(build_match_context("Demo", "Away", "Demo League", "2025/26", "2026-02-14"))
    result = resolve_real_fixture(ctx, {"football_data": "tests/fixtures/v20_one_command_runner/football_data_live_mock.csv"}, tmp_path)
    assert result.suggested_team_names
