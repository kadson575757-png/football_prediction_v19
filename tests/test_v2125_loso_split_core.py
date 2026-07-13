import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import prepare_probe_rows, run_leave_one_season_out


def _rows():
    return prepare_probe_rows(pd.DataFrame([
        {"season": season, "match_date": f"2025-01-0{index}", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.40, "draw_probability": 0.32, "away_win_probability": 0.28, "probability_edge": 0.04}
        for index, season in enumerate(["S1", "S2", "S3"], start=1)
    ]))


def test_leave_one_season_out_has_three_disjoint_rotations():
    training, folds, holdouts = run_leave_one_season_out(_rows(), ["S1", "S2", "S3"])
    assert len(folds) == 3
    assert set(folds["holdout_season"]) == {"S1", "S2", "S3"}
    assert len(training) == 24
    for _, fold in folds.iterrows():
        assert fold["holdout_season"] not in fold["selection_seasons"].split(",")
    assert (holdouts["season"] == holdouts["holdout_season"]).all()
