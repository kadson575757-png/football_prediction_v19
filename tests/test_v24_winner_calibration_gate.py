from tests.v24_test_helpers import make_prediction_results
from football_prediction_v19.analysis.v22_calibration_export import write_calibration_dataset
from football_prediction_v19.analysis.v24_no_decision_diagnostics import write_no_decision_diagnostics
from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics
from football_prediction_v19.analysis.v24_threshold_simulation import write_threshold_simulation
from football_prediction_v19.analysis.v24_confidence_calibration import write_confidence_calibration
from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_winner_calibration_gate(tmp_path):
    source = make_prediction_results(tmp_path / "results.csv")
    diag = tmp_path / "diag"
    write_calibration_dataset(source, diag)
    write_no_decision_diagnostics(source, diag)
    write_probability_diagnostics(source, diag)
    write_threshold_simulation(source, diag)
    write_confidence_calibration(source, diag)
    result = run_v24_winner_calibration_gate(tmp_path / "gate", diag, {"matches_requested": 3, "matches_available": 3, "matches_evaluated": 3, "data_blocked_count": 0, "probabilities_created_count": 3}, min_calibration_matches_required=1)
    assert result["v24_winner_calibration_gate_status"] == "V24_READY_TO_TAG"
