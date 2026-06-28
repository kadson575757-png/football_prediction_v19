from football_prediction_v19.analysis.v24_confidence_calibration import write_confidence_calibration
from tests.v24_test_helpers import make_prediction_results


def test_v24_confidence_calibration_total_count_reported(tmp_path):
    result = write_confidence_calibration(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    assert result["total_count"] == 3

