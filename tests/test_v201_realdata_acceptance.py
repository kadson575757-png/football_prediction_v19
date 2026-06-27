from football_prediction_v19.analysis.v201_realdata_release_gate import run_v201_realdata_release_gate


def test_v201_acceptance_includes_no_odds_and_cache_checks(tmp_path):
    result = run_v201_realdata_release_gate(tmp_path)
    assert result["no_odds_policy_status"] == "PASSED"
    assert result["cache_only_status"] == "PASSED"
    assert result["network_default_off"] is True
