from football_prediction_v19.analysis.v24_confidence_calibration import write_confidence_calibration
from tests.v24_test_helpers import make_prediction_results


def test_v24_confidence_calibration_insufficient_sample_status(tmp_path):
    result = write_confidence_calibration(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out", min_required_rows=10)
    assert result["confidence_calibration_status"] == "INSUFFICIENT_SAMPLE"

