from pathlib import Path

import pandas as pd


def make_fixture_corpus(path: Path, rows: list[dict[str, object]] | None = None) -> Path:
    rows = rows or [
        {"competition": "Premier League", "season": "2025/26", "match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Chelsea", "result_1x2": "", "football_data_available": True, "can_backtest": False},
        {"competition": "Bundesliga", "season": "2025/26", "match_date": "2026-04-12", "home_team": "Bayern Munich", "away_team": "Borussia Dortmund", "result_1x2": "", "football_data_available": True, "can_backtest": False},
        {"competition": "La Liga", "season": "2025/26", "match_date": "2026-05-03", "home_team": "Barcelona", "away_team": "Real Madrid", "result_1x2": "", "football_data_available": True, "can_backtest": False},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path
