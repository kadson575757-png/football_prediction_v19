from pathlib import Path


def test_v25_batch_runner_exists():
    assert Path("scripts/run_match_winner_batch.py").exists()

