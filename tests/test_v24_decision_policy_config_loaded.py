from football_prediction_v19.analysis.v21_winner_decision_policy import load_decision_policy_config


def test_v24_decision_policy_config_loaded():
    config = load_decision_policy_config("config/v24_winner_decision_policy.yaml")
    assert config["active_policy"] == "balanced_results_only_safe"
    assert config["allow_winner_lean_without_xg"] is True

