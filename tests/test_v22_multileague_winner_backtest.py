from pathlib import Path

from scripts.run_v22_multileague_winner_backtest import run_v22_multileague_winner_backtest
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_multileague_winner_backtest(tmp_path):
    result = run_v22_multileague_winner_backtest(
        season="2025/26",
        competitions="Premier League",
        output_dir=str(tmp_path / "out"),
        mock_data_dir=str(make_mock_source_dir(tmp_path)),
        max_matches_per_league=3,
    )
    assert result["v22_multileague_winner_backtest_status"] in {"READY", "INSUFFICIENT_SAMPLE"}
    assert int(result["evaluated_matches"]) >= 1
    assert Path(tmp_path / "out" / "multileague_winner_backtest_results.csv").exists()

