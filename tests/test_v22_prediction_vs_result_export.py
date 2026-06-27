import pandas as pd

from football_prediction_v19.analysis.v22_calibration_export import write_calibration_dataset


def test_v22_prediction_vs_result_export(tmp_path):
    results = tmp_path / "results.csv"
    pd.DataFrame([{
        "competition": "Serie A",
        "match_id": "m2",
        "match_date": "2025-08-02",
        "actual_result": "A",
        "predicted_winner": "AWAY",
        "home_win_probability": 0.2,
        "draw_probability": 0.25,
        "away_win_probability": 0.55,
    }]).to_csv(results, index=False)
    result = write_calibration_dataset(results, tmp_path / "cal")
    frame = pd.read_csv(result["model_prediction_vs_result_path"])
    assert {"predicted_winner", "result_1x2", "probability_assigned_to_actual_result"}.issubset(frame.columns)

