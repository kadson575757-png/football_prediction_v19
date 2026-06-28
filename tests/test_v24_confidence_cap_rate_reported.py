from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics
from tests.v24_test_helpers import make_prediction_results


def test_v24_confidence_cap_rate_reported(tmp_path):
    result = write_probability_diagnostics(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    assert "confidence_cap_rate" in result
    assert result["confidence_cap_rate"] > 0
