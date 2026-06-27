import json

import pandas as pd

from scripts.run_v20_realdata_smoke_suite import run_v20_realdata_smoke_suite


def _mock(tmp_path):
    mock = tmp_path / "mock"; mock.mkdir()
    pd.DataFrame([{"Date": "2025-08-10", "HomeTeam": "Demo Home", "AwayTeam": "Demo Away", "FTHG": 2, "FTAG": 1, "FTR": "H"}]).to_csv(mock / "football_data_live_mock.csv", index=False)
    (mock / "understat_league_mock.json").write_text(json.dumps({"matches": [{"date": "2025-08-10", "home_team": "Demo Home", "away_team": "Demo Away", "home_xg": 1.7, "away_xg": 0.9}]}), encoding="utf-8")
    path = tmp_path / "matches.yaml"
    path.write_text("matches:\n  - home_team: Demo Home\n    away_team: Demo Away\n    competition: Demo League\n    season: 2025/26\n    match_date: 2026-02-15\n", encoding="utf-8")
    return mock, path


def test_realdata_smoke_no_odds_is_not_data_blocked(tmp_path):
    mock, matches = _mock(tmp_path)
    result = run_v20_realdata_smoke_suite(matches=str(matches), output_dir=str(tmp_path / "out"), mock_data_dir=str(mock), cache_dir=str(tmp_path / "cache"))
    assert result["matches_data_blocked"] == 0
    assert result["automatic_betting_enabled"] is False
