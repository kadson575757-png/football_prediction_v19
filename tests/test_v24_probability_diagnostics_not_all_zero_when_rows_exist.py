from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics
from tests.v24_test_helpers import make_prediction_results


def test_v24_probability_diagnostics_not_all_zero_when_rows_exist(tmp_path):
    result = write_probability_diagnostics(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    assert result["probability_rows_count"] > 0
    assert result["average_top_probability"] > 0

