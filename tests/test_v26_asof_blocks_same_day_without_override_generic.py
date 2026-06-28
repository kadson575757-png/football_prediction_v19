from football_prediction_v19.analysis.v26_asof_guard import evaluate_asof_guard


def test_v26_asof_blocks_same_day_without_override_generic():
    result = evaluate_asof_guard("2026-03-01", "2026-03-01")
    assert result["asof_guard_status"] == "BLOCKED"
    assert result["leakage_warning"] is True

