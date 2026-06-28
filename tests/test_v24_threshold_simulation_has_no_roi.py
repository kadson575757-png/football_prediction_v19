import pandas as pd
from football_prediction_v19.analysis.v24_threshold_simulation import write_threshold_simulation
from tests.v24_test_helpers import make_prediction_results


def test_v24_threshold_simulation_has_no_roi(tmp_path):
    result = write_threshold_simulation(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    frame = pd.read_csv(result["threshold_simulation_results_path"])
    lowered = " ".join(frame.columns).lower()
    assert "roi" not in lowered and "stake" not in lowered and "profit" not in lowered

