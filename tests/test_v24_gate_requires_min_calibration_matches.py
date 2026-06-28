from tests.test_v24_winner_calibration_gate import test_v24_winner_calibration_gate
from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_gate_requires_min_calibration_matches(tmp_path):
    test_v24_winner_calibration_gate(tmp_path)
    result = run_v24_winner_calibration_gate(tmp_path / "gate2", tmp_path / "diag", {"matches_requested": 25, "matches_available": 25, "matches_evaluated": 25, "data_blocked_count": 0, "probabilities_created_count": 25}, min_calibration_matches_required=50)
    assert result["sufficient_calibration_sample"] is False

