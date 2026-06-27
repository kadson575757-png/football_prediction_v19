from football_prediction_v19.analysis.v20_historical_model_engine import run_v20_model_engine


def test_model_policy_blocks_without_football_data_and_penalizes_missing_sources(tmp_path):
    blocked = run_v20_model_engine({"leakage_status": "CLEAN", "table_available": False, "data_quality_score": 0.4}, tmp_path)
    assert blocked["model_status"] == "MODEL_BLOCKED"

    partial = run_v20_model_engine({"leakage_status": "CLEAN", "table_available": True, "xg_available": False, "odds_available": False, "data_quality_score": 1.0}, tmp_path)
    assert partial["model_status"] == "MODEL_PARTIAL"
    assert partial["model_confidence"] < 0.7
