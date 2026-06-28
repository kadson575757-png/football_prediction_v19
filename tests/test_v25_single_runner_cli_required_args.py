import pytest
from scripts.run_match_winner_analysis import main


def test_v25_single_runner_cli_required_args():
    with pytest.raises(SystemExit):
        main([])

