import pandas as pd

from football_prediction_v19.analysis.v291_home_away_ppg_indicator import build_home_away_ppg_indicator


def test_v291_home_away_ppg_indicator_core(monkeypatch, tmp_path):
    normalized = tmp_path / "football_data_live_normalized.csv"
    pd.DataFrame(
        [
            {"Date": "2026-01-01", "HomeTeam": "Arsenal", "AwayTeam": "Team A", "FTHG": 2, "FTAG": 0, "FTR": "H"},
            {"Date": "2026-01-08", "HomeTeam": "Arsenal", "AwayTeam": "Team B", "FTHG": 1, "FTAG": 1, "FTR": "D"},
            {"Date": "2026-01-15", "HomeTeam": "Arsenal", "AwayTeam": "Team C", "FTHG": 0, "FTAG": 1, "FTR": "A"},
            {"Date": "2026-01-02", "HomeTeam": "Team D", "AwayTeam": "Chelsea", "FTHG": 0, "FTAG": 2, "FTR": "A"},
            {"Date": "2026-01-09", "HomeTeam": "Team E", "AwayTeam": "Chelsea", "FTHG": 1, "FTAG": 1, "FTR": "D"},
            {"Date": "2026-01-16", "HomeTeam": "Team F", "AwayTeam": "Chelsea", "FTHG": 3, "FTAG": 0, "FTR": "H"},
            {"Date": "2026-03-01", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": 5, "FTAG": 0, "FTR": "H"},
            {"Date": "2026-03-02", "HomeTeam": "Arsenal", "AwayTeam": "Team G", "FTHG": 5, "FTAG": 0, "FTR": "H"},
        ]
    ).to_csv(normalized, index=False)
    monkeypatch.setattr(
        "football_prediction_v19.analysis.v291_home_away_ppg_indicator.run_football_data_live_adapter",
        lambda *args, **kwargs: {"football_data_live_status": "CACHE_HIT", "football_data_live_normalized_path": str(normalized)},
    )

    result = build_home_away_ppg_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01")

    assert result["home_home_matches_before_match"] == 3
    assert result["away_away_matches_before_match"] == 3
    assert result["home_home_points_before_match"] == 4
    assert result["away_away_points_before_match"] == 4
    assert result["home_home_ppg_before_match"] == 1.3333
    assert result["away_away_ppg_before_match"] == 1.3333
    assert result["home_away_ppg_diff"] == 0.0
    assert result["indicator_quality"] == "FULL"

