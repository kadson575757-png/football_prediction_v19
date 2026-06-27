import pandas as pd

from football_prediction_v19.analysis.v20_no_leakage_backtest_runner import run_no_leakage_backtest


def test_no_leakage_backtest_reports_source_coverage_without_odds(tmp_path):
    matches = tmp_path / "matches.csv"
    pd.DataFrame([{"home_team": "Demo Home", "away_team": "Demo Away", "competition": "Demo League", "season": "2025/26", "match_date": "2026-02-20", "actual_result": "H"}]).to_csv(matches, index=False)
    result = run_no_leakage_backtest(matches, tmp_path / "out", mock_data_dir="tests/fixtures/v20_historical_internet_prediction", max_matches=1)
    assert result["source_coverage_without_odds"] is True
    assert "roi" not in result
