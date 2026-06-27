import pandas as pd

from football_prediction_v19.analysis.v20_understat_live_adapter import understat_candidate_matches


def test_understat_candidate_search_wrong_date():
    df = pd.DataFrame([{"date": "2026-02-15", "home_team": "Arsenal", "away_team": "Chelsea", "home_xg": 1.2, "away_xg": 0.8}])
    rows = understat_candidate_matches(df, "Arsenal", "Chelsea", "2026-02-14")
    assert rows
    assert rows[0]["reason"] == "date_tolerance"
