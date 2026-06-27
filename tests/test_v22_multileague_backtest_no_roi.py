from scripts.run_v22_multileague_winner_backtest import run_v22_multileague_winner_backtest
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_multileague_backtest_no_roi(tmp_path):
    result = run_v22_multileague_winner_backtest(
        season="2025/26",
        competitions="Premier League",
        output_dir=str(tmp_path / "out"),
        mock_data_dir=str(make_mock_source_dir(tmp_path)),
        max_matches_per_league=2,
    )
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False

