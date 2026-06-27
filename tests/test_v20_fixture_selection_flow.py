import json

import pandas as pd

from scripts.search_v20_real_fixtures import run_search_v20_real_fixtures


def _mock_sources(tmp_path):
    mock = tmp_path / "mock"
    mock.mkdir()
    pd.DataFrame(
        [
            {"Date": "2026-02-14", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": "", "FTAG": "", "FTR": ""},
            {"Date": "2026-03-01", "HomeTeam": "Arsenal", "AwayTeam": "Liverpool", "FTHG": "", "FTAG": "", "FTR": ""},
        ]
    ).to_csv(mock / "football_data_live_mock.csv", index=False)
    (mock / "understat_league_mock.json").write_text(
        json.dumps(
            {
                "matches": [
                    {"date": "2026-02-14", "home_team": "Arsenal", "away_team": "Chelsea", "home_xg": 1.4, "away_xg": 1.2}
                ]
            }
        ),
        encoding="utf-8",
    )
    return mock


def test_fixture_selection_finds_team_opponent_candidate(tmp_path):
    result = run_search_v20_real_fixtures(
        competition="Premier League",
        season="2025/26",
        team="Arsenal",
        opponent="Chelsea",
        date_from="2026-01-01",
        date_to="2026-03-31",
        output_dir=str(tmp_path / "out"),
        mock_data_dir=str(_mock_sources(tmp_path)),
        source_profile="config/v20_internet_sources.yaml",
        cache_dir=str(tmp_path / "cache"),
        enable_network=False,
    )
    assert result["fixture_search_status"] == "READY"
    assert result["matches_found"] >= 1
