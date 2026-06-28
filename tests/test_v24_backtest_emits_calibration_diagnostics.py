from pathlib import Path
from tests.v24_test_helpers import run_v24_backtest


def test_v24_backtest_emits_calibration_diagnostics(tmp_path):
    result = run_v24_backtest(tmp_path)
    assert result["calibration_diagnostics_status"] == "PASSED"
    assert Path(result["calibration_dataset_csv_path"]).exists()

