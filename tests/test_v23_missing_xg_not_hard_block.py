from football_prediction_v19.analysis.v23_data_block_audit import classify_block_reason


def test_v23_missing_xg_not_hard_block():
    result = classify_block_reason({"xg_available": False, "odds_available": True})
    assert result["block_reason_code"] == "missing_xg"
    assert result["is_hard_block"] is False
    assert result["should_have_been_non_blocking"] is True

