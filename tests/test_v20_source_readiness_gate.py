from football_prediction_v19.analysis.v20_source_readiness_gate import evaluate_source_readiness


def test_source_readiness_gate_rules():
    assert evaluate_source_readiness("NOT_FOUND", "ASOF_READY", "CLEAN", {"table_available": True})["source_readiness"] == "DATA_BLOCKED"
    assert evaluate_source_readiness("RESOLVED", "ASOF_READY", "BLOCKED", {"table_available": True})["source_readiness"] == "DATA_BLOCKED"
    assert evaluate_source_readiness("RESOLVED", "ASOF_READY", "CLEAN", {"table_available": True, "xg_available": False, "odds_available": True})["source_readiness"] == "READY_FOR_ANALYST_LEAN"
    assert evaluate_source_readiness("RESOLVED", "ASOF_READY", "CLEAN", {"table_available": True, "xg_available": True, "odds_available": True})["source_readiness"] == "READY_FOR_MODEL"
