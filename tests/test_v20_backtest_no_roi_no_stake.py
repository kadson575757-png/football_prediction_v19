import pandas as pd

from football_prediction_v19.analysis.v20_no_leakage_backtest_runner import run_no_leakage_backtest


def test_backtest_without_odds_has_no_roi_or_stake_outputs(tmp_path):
    matches = tmp_path / "matches.csv"
    pd.DataFrame([{"home_team": "Demo Home", "away_team": "Demo Away", "competition": "Demo League", "season": "2025/26", "match_date": "2026-02-20", "actual_result": "H"}]).to_csv(matches, index=False)
    result = run_no_leakage_backtest(matches, tmp_path / "out", mock_data_dir="tests/fixtures/v20_historical_internet_prediction", max_matches=1)
    text = (tmp_path / "out" / "v20_no_leakage_backtest_metrics.json").read_text(encoding="utf-8").lower()
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert "stake" not in text
    assert "roi" not in text
