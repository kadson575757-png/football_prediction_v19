from football_prediction_v19.analysis.v20_source_readiness_gate import evaluate_source_readiness


def test_missing_odds_alone_does_not_data_block(tmp_path):
    result = evaluate_source_readiness(
        "RESOLVED",
        "READY",
        "CLEAN",
        {"table_available": True, "form_available": True, "xg_available": True, "odds_available": False},
        tmp_path,
    )
    assert result["source_readiness"] == "READY_FOR_ANALYST_LEAN"
    assert "odds missing" in " ".join(result["readiness_reasons"])


def test_missing_xg_and_odds_is_no_bet_not_data_block(tmp_path):
    result = evaluate_source_readiness(
        "RESOLVED",
        "READY",
        "CLEAN",
        {"table_available": True, "form_available": True, "xg_available": False, "odds_available": False},
        tmp_path,
    )
    assert result["source_readiness"] == "NO_BET_REQUIRED"
