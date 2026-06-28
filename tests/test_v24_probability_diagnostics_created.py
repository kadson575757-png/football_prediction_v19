from pathlib import Path
from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics
from tests.v24_test_helpers import make_prediction_results


def test_v24_probability_diagnostics_created(tmp_path):
    result = write_probability_diagnostics(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    assert result["probability_diagnostics_status"] == "PASSED"
    assert Path(result["probability_distribution_diagnostics_path"]).exists()

