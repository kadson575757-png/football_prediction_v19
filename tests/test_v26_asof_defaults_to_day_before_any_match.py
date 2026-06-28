from football_prediction_v19.analysis.v26_asof_guard import evaluate_asof_guard


def test_v26_asof_defaults_to_day_before_any_match():
    result = evaluate_asof_guard("2026-03-01")
    assert result["as_of_date"] == "2026-02-28"
    assert result["asof_guard_status"] == "CLEAN"

