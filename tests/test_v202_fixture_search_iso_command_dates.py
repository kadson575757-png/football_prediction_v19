import json

import pandas as pd

from scripts.search_v20_real_fixtures import run_search_v20_real_fixtures


def test_v202_fixture_search_iso_command_dates(tmp_path):
    mock = tmp_path / "mock"; mock.mkdir()
    pd.DataFrame([{"Date": "2025-08-23", "HomeTeam": "Arsenal", "AwayTeam": "Leeds United", "FTHG": "", "FTAG": "", "FTR": ""}]).to_csv(mock / "football_data_live_mock.csv", index=False)
    (mock / "understat_league_mock.json").write_text(json.dumps({"matches": []}), encoding="utf-8")
    out = tmp_path / "out"
    run_search_v20_real_fixtures(competition="Premier League", season="2025/26", team="Arsenal", opponent="Leeds", date_from="23/08/2025", date_to="", output_dir=str(out), mock_data_dir=str(mock), source_profile="config/v20_internet_sources.yaml")
    rows = pd.read_csv(out / "fixture_search_results.csv")
    assert rows.loc[0, "match_date"] == "2025-08-23"
    assert '--match-date "2025-08-23"' in rows.loc[0, "recommended_run_command"]
