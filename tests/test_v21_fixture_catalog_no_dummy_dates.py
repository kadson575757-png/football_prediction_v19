from football_prediction_v19.analysis.v21_season_fixture_catalog import canonical_match_id_for


def test_v21_fixture_catalog_no_dummy_dates():
    match_id = canonical_match_id_for("Premier League", "2025/26", "23/08/2025", "Arsenal", "Leeds")
    assert "2025-08-23" in match_id
    assert "2024-08-23" not in match_id
