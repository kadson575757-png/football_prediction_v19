from pathlib import Path

from tests.v23_test_helpers import run_results_only_backtest


def test_v23_missing_data_non_blocking_report_created(tmp_path):
    run_results_only_backtest(tmp_path)
    assert Path(tmp_path / "out" / "missing_data_non_blocking_report.md").exists()
