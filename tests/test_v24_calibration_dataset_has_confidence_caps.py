import pandas as pd
from football_prediction_v19.analysis.v22_calibration_export import write_calibration_dataset
from tests.v24_test_helpers import make_prediction_results


def test_v24_calibration_dataset_has_confidence_caps(tmp_path):
    result = write_calibration_dataset(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    frame = pd.read_csv(result["calibration_dataset_csv_path"])
    assert {"confidence_cap_applied", "confidence_cap_reason"}.issubset(frame.columns)
    assert frame["confidence_cap_applied"].any()

