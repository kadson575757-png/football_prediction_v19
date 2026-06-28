import pandas as pd
from football_prediction_v19.analysis.v24_multileague_calibration_dashboard import write_multileague_calibration_dashboard
from tests.v24_test_helpers import make_prediction_results


def test_v24_multileague_no_decision_reason_summary(tmp_path):
    write_multileague_calibration_dashboard(make_prediction_results(tmp_path / "results.csv"), tmp_path / "out")
    frame = pd.read_csv(tmp_path / "out" / "league_no_decision_reasons.csv")
    assert "primary_reason" in frame.columns

