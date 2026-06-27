import pandas as pd

from football_prediction_v19.analysis.v22_calibration_export import write_calibration_dataset


def test_v22_calibration_dataset_created(tmp_path):
    results = tmp_path / "results.csv"
    pd.DataFrame([{
        "competition": "Premier League",
        "match_id": "m1",
        "match_date": "2025-08-01",
        "actual_result": "H",
        "predicted_winner": "HOME",
        "decision_class": "CLEAR_HOME_EDGE",
        "home_win_probability": 0.55,
        "draw_probability": 0.25,
        "away_win_probability": 0.20,
    }]).to_csv(results, index=False)
    result = write_calibration_dataset(results, tmp_path / "cal")
    assert result["v22_calibration_export_status"] == "READY"
    assert pd.read_csv(result["calibration_dataset_csv_path"]).loc[0, "correct_top1"]

