from football_prediction_v19.analysis.v20_historical_match_context import normalize_match_date


def test_v21_date_normalization():
    assert normalize_match_date("2025-08-23") == "2025-08-23"
    assert normalize_match_date("23/08/2025") == "2025-08-23"
    assert normalize_match_date("23.08.2025") == "2025-08-23"
