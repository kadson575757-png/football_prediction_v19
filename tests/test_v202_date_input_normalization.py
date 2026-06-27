from football_prediction_v19.analysis.v20_historical_match_context import build_match_context, normalize_match_date


def test_v202_date_input_normalization():
    assert normalize_match_date("23/08/2025") == "2025-08-23"
    assert normalize_match_date("23.08.2025") == "2025-08-23"
    assert build_match_context("Arsenal", "Leeds", "Premier League", "2025/26", "23/08/2025").match_date == "2025-08-23"
