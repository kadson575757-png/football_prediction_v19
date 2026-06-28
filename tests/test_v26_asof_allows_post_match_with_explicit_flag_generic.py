from football_prediction_v19.analysis.v26_asof_guard import evaluate_asof_guard


def test_v26_asof_allows_post_match_with_explicit_flag_generic():
    result = evaluate_asof_guard("2026-03-01", "2026-03-02", True)
    assert result["asof_guard_status"] == "WARNING"
    assert result["post_match_analysis"] is True

