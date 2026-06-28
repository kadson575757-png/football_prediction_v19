from pathlib import Path
from football_prediction_v19.analysis.v24_multileague_calibration_dashboard import write_multileague_calibration_dashboard
from tests.v24_test_helpers import make_prediction_results


def test_v24_multileague_calibration_dashboard(tmp_path):
    result = write_multileague_calibration_dashboard(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    assert result["multileague_calibration_status"] == "PASSED"
    assert Path(result["multileague_calibration_dashboard_path"]).exists()

