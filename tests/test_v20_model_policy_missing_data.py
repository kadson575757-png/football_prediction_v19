from football_prediction_v19.analysis.v20_historical_model_engine import run_v20_model_engine


def test_model_policy_missing_table_blocks(tmp_path):
    result = run_v20_model_engine({"leakage_status": "CLEAN", "table_available": False, "data_quality_score": 1}, tmp_path)
    assert result["model_status"] == "MODEL_BLOCKED"
