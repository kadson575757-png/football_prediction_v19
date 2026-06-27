from football_prediction_v19.analysis.v23_data_block_audit import classify_block_reason


def test_v23_missing_odds_not_hard_block():
    result = classify_block_reason({"xg_available": True, "odds_available": False})
    assert result["block_reason_code"] == "missing_odds"
    assert result["is_hard_block"] is False

