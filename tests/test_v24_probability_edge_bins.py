import pandas as pd
from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics
from tests.v24_test_helpers import make_prediction_results


def test_v24_probability_edge_bins(tmp_path):
    result = write_probability_diagnostics(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    bins = pd.read_csv(result["probability_distribution_bins_path"])
    assert "top_edge_over_0_07" in set(bins["bin"])

