import pandas as pd

from football_prediction_v19.analysis.v21_season_fixture_catalog import join_fixture_sources


def test_v21_fixture_catalog_alias_suggestions():
    fd = pd.DataFrame([{"Date": "2025-08-23", "HomeTeam": "Arsenal", "AwayTeam": "Leeds", "FTR": ""}])
    us = pd.DataFrame([{"id": "1", "date": "2025-08-23", "home_team": "Arsenal", "away_team": "Leeds United", "home_xg": 2.0, "away_xg": 0.8}])
    _, _, _, aliases = join_fixture_sources(fd, us, "Premier League", "2025/26", "TIER_1_FULL_XG")
    assert "Leeds United" in set(aliases["understat_team"])
