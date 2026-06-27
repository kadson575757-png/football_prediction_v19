from football_prediction_v19.analysis.v20_source_readiness_gate import evaluate_source_readiness


def test_missing_odds_or_xg_alone_not_data_blocked():
    no_odds = evaluate_source_readiness("RESOLVED", "ASOF_PARTIAL", "CLEAN", {"table_available": True, "xg_available": True, "odds_available": False})
    assert no_odds["source_readiness"] == "READY_FOR_ANALYST_LEAN"
    no_xg = evaluate_source_readiness("RESOLVED", "ASOF_PARTIAL", "CLEAN", {"table_available": True, "xg_available": False, "odds_available": True})
    assert no_xg["source_readiness"] == "READY_FOR_ANALYST_LEAN"
    neither = evaluate_source_readiness("RESOLVED", "ASOF_PARTIAL", "CLEAN", {"table_available": True, "xg_available": False, "odds_available": False})
    assert neither["source_readiness"] == "NO_BET_REQUIRED"
    missing_fixture = evaluate_source_readiness("NOT_FOUND", "ASOF_READY", "CLEAN", {"table_available": True, "xg_available": True, "odds_available": True})
    assert missing_fixture["source_readiness"] == "DATA_BLOCKED"
