from scripts.run_v22_multileague_winner_backtest import run_v22_multileague_winner_backtest
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_multileague_backtest_reports_sample_size(tmp_path):
    result = run_v22_multileague_winner_backtest(
        season="2025/26",
        competitions="Premier League",
        output_dir=str(tmp_path / "out"),
        mock_data_dir=str(make_mock_source_dir(tmp_path, n=8)),
        max_matches_per_league=2,
    )
    assert "total_matches_available" in result
    assert "evaluated_matches" in result
    assert "statistical_validity" in result

