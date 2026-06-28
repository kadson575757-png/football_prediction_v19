import pandas as pd
from football_prediction_v19.analysis.v24_confidence_calibration import write_confidence_calibration
from tests.v24_test_helpers import make_prediction_results


def test_v24_confidence_calibration_bins(tmp_path):
    result = write_confidence_calibration(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    bins = pd.read_csv(result["confidence_calibration_bins_path"])
    assert len(bins) == 7

