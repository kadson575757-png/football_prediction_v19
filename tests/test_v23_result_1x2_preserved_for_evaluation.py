import pandas as pd

from tests.v23_test_helpers import run_results_only_backtest


def test_v23_result_1x2_preserved_for_evaluation(tmp_path):
    run_results_only_backtest(tmp_path)
    results = pd.read_csv(tmp_path / "out" / "winner_backtest_results.csv")
    assert set(results["actual_result"]).issubset({"H", "D", "A"})

