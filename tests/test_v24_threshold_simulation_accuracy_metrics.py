import pandas as pd
from football_prediction_v19.analysis.v24_threshold_simulation import write_threshold_simulation
from tests.v24_test_helpers import make_prediction_results


def test_v24_threshold_simulation_accuracy_metrics(tmp_path):
    result = write_threshold_simulation(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    frame = pd.read_csv(result["threshold_simulation_results_path"])
    assert {"top1_accuracy_all_model_outputs", "top1_accuracy_decisions_only", "brier_score_all", "brier_score_decisions_only"}.issubset(frame.columns)

