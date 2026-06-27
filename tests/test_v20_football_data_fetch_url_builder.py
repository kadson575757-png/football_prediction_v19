from football_prediction_v19.analysis.v20_football_data_live_adapter import build_football_data_url, normalize_football_data_csv
from football_prediction_v19.analysis.v20_source_league_resolver import football_data_season_code
import pandas as pd


def test_football_data_season_code_and_url_builder():
    assert football_data_season_code("2025/26") == "2526"
    assert football_data_season_code("2024/25") == "2425"
    assert football_data_season_code("2023/24") == "2324"
    assert build_football_data_url("2025/26", "E0") == "https://www.football-data.co.uk/mmz4281/2526/E0.csv"


def test_football_data_csv_normalization_adds_required_columns():
    df = normalize_football_data_csv(pd.DataFrame([{"Date": "2026-02-14", "HomeTeam": "A", "AwayTeam": "B", "FTHG": 1, "FTAG": 0, "FTR": "H"}]))
    assert ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "B365H", "B365D", "B365A"] == list(df.columns)
