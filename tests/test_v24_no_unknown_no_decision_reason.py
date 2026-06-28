import pandas as pd
from football_prediction_v19.analysis.v24_no_decision_diagnostics import write_no_decision_diagnostics
from tests.v24_test_helpers import make_prediction_results


def test_v24_no_unknown_no_decision_reason(tmp_path):
    result = write_no_decision_diagnostics(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    frame = pd.read_csv(result["no_decision_diagnostics_csv_path"])
    assert "UNKNOWN_NO_DECISION_REASON" not in set(frame["primary_reason"])

