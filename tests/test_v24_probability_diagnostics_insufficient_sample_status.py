from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics
from tests.v24_test_helpers import make_prediction_results


def test_v24_probability_diagnostics_insufficient_sample_status(tmp_path):
    result = write_probability_diagnostics(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out", min_required_rows=10)
    assert result["probability_diagnostics_status"] == "INSUFFICIENT_SAMPLE"
    assert result["sample_warning"] is True

