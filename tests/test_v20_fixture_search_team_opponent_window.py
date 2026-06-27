import json

import pandas as pd

from scripts.search_v20_real_fixtures import run_search_v20_real_fixtures


def test_fixture_search_respects_team_opponent_date_window(tmp_path):
    mock = tmp_path / "mock"
    mock.mkdir()
    pd.DataFrame(
        [
            {"Date": "2026-02-14", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": "", "FTAG": "", "FTR": ""},
            {"Date": "2026-04-14", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": "", "FTAG": "", "FTR": ""},
        ]
    ).to_csv(mock / "football_data_live_mock.csv", index=False)
    (mock / "understat_league_mock.json").write_text(json.dumps({"matches": []}), encoding="utf-8")
    out = tmp_path / "out"
    run_search_v20_real_fixtures(
        competition="Premier League",
        season="2025/26",
        team="Arsenal",
        opponent="Chelsea",
        date_from="2026-02-01",
        date_to="2026-03-01",
        output_dir=str(out),
        mock_data_dir=str(mock),
        source_profile="config/v20_internet_sources.yaml",
        cache_dir=str(tmp_path / "cache"),
        enable_network=False,
    )
    rows = pd.read_csv(out / "fixture_search_results.csv")
    assert set(rows["match_date"]) == {"2026-02-14"}
