import pandas as pd

from football_prediction_v19.analysis.v20_football_data_live_adapter import football_data_candidate_matches


def test_football_data_candidate_search_exact_and_wrong_date():
    df = pd.DataFrame([{"Date": "2026-02-15", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": 2, "FTAG": 1, "FTR": "H"}])
    rows = football_data_candidate_matches(df, "Arsenal", "Chelsea", "2026-02-14")
    assert rows
    assert rows[0]["reason"] == "date_tolerance"
