from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


def test_known_leagues_are_mapped_without_demo_hardcoding(tmp_path):
    mapping = resolve_source_league("Premier League", "2025/26", tmp_path)
    assert mapping.status == "RESOLVED"
    assert mapping.football_data_code == "E0"
    assert mapping.understat_league_code == "EPL"
    assert mapping.odds_api_sport_key == "soccer_epl"
    assert (tmp_path / "source_league_mapping.json").exists()


def test_unknown_league_is_unsupported_or_partial():
    mapping = resolve_source_league("Moon League", "2025/26")
    assert mapping.status == "UNSUPPORTED"
    assert mapping.football_data_code == ""
