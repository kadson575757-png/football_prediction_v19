from pathlib import Path

from tests.v23_test_helpers import run_results_only_backtest


def test_v23_data_block_audit_created(tmp_path):
    run_results_only_backtest(tmp_path)
    assert Path(tmp_path / "out" / "data_block_audit.csv").exists()
    assert Path(tmp_path / "out" / "data_block_audit.json").exists()
    assert Path(tmp_path / "out" / "data_block_audit_report.md").exists()

