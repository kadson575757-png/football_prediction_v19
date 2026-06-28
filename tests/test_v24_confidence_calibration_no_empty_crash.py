import pandas as pd
from football_prediction_v19.analysis.v24_confidence_calibration import write_confidence_calibration


def test_v24_confidence_calibration_no_empty_crash(tmp_path):
    path = tmp_path / "empty.csv"
    pd.DataFrame(columns=["home_win_probability", "draw_probability", "away_win_probability"]).to_csv(path, index=False)
    result = write_confidence_calibration(path, tmp_path / "out")
    assert result["confidence_calibration_status"] == "EMPTY_DATASET"
