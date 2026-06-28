from pathlib import Path
from football_prediction_v19.analysis.v24_threshold_simulation import write_threshold_simulation
from tests.v24_test_helpers import make_prediction_results


def test_v24_threshold_simulation_created(tmp_path):
    result = write_threshold_simulation(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    assert result["threshold_simulation_status"] == "PASSED"
    assert Path(result["threshold_simulation_results_path"]).exists()

