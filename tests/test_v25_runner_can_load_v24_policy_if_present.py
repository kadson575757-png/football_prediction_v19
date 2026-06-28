from pathlib import Path


def test_v25_runner_can_load_v24_policy_if_present():
    assert Path("config/v24_winner_decision_policy.yaml").exists()

