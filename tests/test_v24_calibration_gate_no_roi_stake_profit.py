from tests.test_v24_winner_calibration_gate import test_v24_winner_calibration_gate


def test_v24_calibration_gate_no_roi_stake_profit(tmp_path):
    test_v24_winner_calibration_gate(tmp_path)
    text = (tmp_path / "gate" / "v24_winner_calibration_gate_summary.csv").read_text(encoding="utf-8").lower()
    assert "automatic_betting_enabled" in text

