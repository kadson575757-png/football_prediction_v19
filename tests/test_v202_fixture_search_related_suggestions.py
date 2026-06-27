import json

import pandas as pd

from scripts.search_v20_real_fixtures import run_search_v20_real_fixtures


def test_v202_fixture_search_related_suggestions(tmp_path):
    mock = tmp_path / "mock"; mock.mkdir()
    pd.DataFrame([
        {"Date": "2025-08-30", "HomeTeam": "Arsenal", "AwayTeam": "Leeds United", "FTHG": "", "FTAG": "", "FTR": ""}
    ]).to_csv(mock / "football_data_live_mock.csv", index=False)
    (mock / "understat_league_mock.json").write_text(json.dumps({"matches": []}), encoding="utf-8")
    out = tmp_path / "out"
    result = run_search_v20_real_fixtures(competition="Premier League", season="2025/26", team="Arsenal", opponent="Chelsea", date_from="2025-08-01", date_to="2025-09-30", output_dir=str(out), mock_data_dir=str(mock), source_profile="config/v20_internet_sources.yaml")
    related = pd.read_csv(out / "fixture_search_related_suggestions.csv")
    assert result["matches_found"] == 0
    assert len(related) == 1
