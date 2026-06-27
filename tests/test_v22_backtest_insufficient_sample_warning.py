import pandas as pd

from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def test_v22_backtest_insufficient_sample_warning(tmp_path):
    matches = tmp_path / "matches.csv"
    pd.DataFrame([{"home_team": "Demo Home", "away_team": "Demo Away", "competition": "Premier League", "season": "2025/26", "match_date": "2026-02-15", "actual_result": "H"}]).to_csv(matches, index=False)
    result = run_v21_winner_backtest(matches, tmp_path / "out", max_matches=50, mock_data_dir="tests/fixtures/v20_live_source_adapters")
    assert result["corpus_status"] == "INSUFFICIENT_SAMPLE"
    assert result["statistical_validity"] == "LOW"
    assert result["sample_warning"] is True
