import json
from pathlib import Path

import pandas as pd

from scripts.run_v20_realdata_smoke_suite import run_v20_realdata_smoke_suite


def _live_fallback_without_odds(tmp_path):
    mock = tmp_path / "mock"
    mock.mkdir()
    pd.DataFrame(
        [
            {"Date": "2025-08-10", "HomeTeam": "Demo Home", "AwayTeam": "Demo Away", "FTHG": 2, "FTAG": 1, "FTR": "H"},
            {"Date": "2025-09-10", "HomeTeam": "Other FC", "AwayTeam": "Demo Home", "FTHG": 1, "FTAG": 1, "FTR": "D"},
            {"Date": "2025-10-10", "HomeTeam": "Demo Away", "AwayTeam": "Other FC", "FTHG": 3, "FTAG": 1, "FTR": "H"},
        ]
    ).to_csv(mock / "football_data_live_mock.csv", index=False)
    (mock / "understat_league_mock.json").write_text(
        json.dumps({"matches": [{"date": "2025-08-10", "home_team": "Demo Home", "away_team": "Demo Away", "home_xg": 1.7, "away_xg": 0.9}]}),
        encoding="utf-8",
    )
    return mock


def _matches_file(tmp_path):
    path = tmp_path / "matches.yaml"
    path.write_text("matches:\n  - home_team: Demo Home\n    away_team: Demo Away\n    competition: Demo League\n    season: 2025/26\n    match_date: 2026-02-15\n", encoding="utf-8")
    return path


def test_realdata_smoke_suite_runs_without_odds_key(tmp_path):
    result = run_v20_realdata_smoke_suite(matches=str(_matches_file(tmp_path)), output_dir=str(tmp_path / "out"), mock_data_dir=str(_live_fallback_without_odds(tmp_path)), cache_dir=str(tmp_path / "cache"))
    assert result["matches_total"] == 1
    assert result["odds_missing_key_count"] == 1
    assert result["matches_data_blocked"] == 0
    assert Path(tmp_path / "out" / "v20_realdata_smoke_results.csv").exists()
