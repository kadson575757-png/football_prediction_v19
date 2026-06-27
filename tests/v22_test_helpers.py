import json
from pathlib import Path

import pandas as pd


def make_mock_source_dir(tmp_path: Path, n: int = 12) -> Path:
    mock = tmp_path / "mock"
    mock.mkdir()
    rows = []
    xg_rows = []
    for i in range(n):
        day = 1 + i
        date = f"2025-08-{day:02d}"
        home = f"Team {i % 4}"
        away = f"Team {(i + 1) % 4}"
        completed = i < n - 2
        rows.append({"Date": date, "HomeTeam": home, "AwayTeam": away, "FTHG": 2 if completed else "", "FTAG": 1 if completed else "", "FTR": "H" if completed else ""})
        xg_rows.append({"id": str(i), "date": date, "home_team": home, "away_team": away, "home_xg": 1.5, "away_xg": 0.9})
    pd.DataFrame(rows).to_csv(mock / "football_data_live_mock.csv", index=False)
    (mock / "understat_league_mock.json").write_text(json.dumps({"matches": xg_rows}), encoding="utf-8")
    return mock
