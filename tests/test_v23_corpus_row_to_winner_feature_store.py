import pandas as pd

from tests.v23_test_helpers import run_results_only_backtest


def test_v23_corpus_row_to_winner_feature_store(tmp_path):
    run_results_only_backtest(tmp_path)
    features = pd.read_csv(tmp_path / "out" / "match_1" / "winner_feature_store.csv")
    assert {"home_points_per_game_asof", "form_edge", "source_quality_band", "leakage_status"}.issubset(features.columns)

