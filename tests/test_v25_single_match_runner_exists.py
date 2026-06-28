from pathlib import Path


def test_v25_single_match_runner_exists():
    assert Path("scripts/run_match_winner_analysis.py").exists()

