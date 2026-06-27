import pandas as pd

from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def test_v23_backtest_detects_all_blocked_as_failure(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame([{"home_team": "", "away_team": "B", "competition": "Premier League", "season": "2025/26", "match_date": "2025-08-01", "actual_result": "H", "football_data_available": True, "result_1x2": "H", "can_backtest": True} for _ in range(10)]).to_csv(path, index=False)
    result = run_v21_winner_backtest(None, tmp_path / "out", corpus_path=path, min_matches_required=2)
    assert result["v21_winner_backtest_status"] == "BLOCKING_BUG_DETECTED"

