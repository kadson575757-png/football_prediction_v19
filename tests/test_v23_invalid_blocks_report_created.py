from pathlib import Path

from tests.v23_test_helpers import run_results_only_backtest


def test_v23_invalid_blocks_report_created(tmp_path):
    run_results_only_backtest(tmp_path)
    assert Path(tmp_path / "out" / "invalid_blocks_report.md").exists()

