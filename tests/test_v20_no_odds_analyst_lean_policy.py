from football_prediction_v19.analysis.v20_historical_model_engine import run_v20_model_engine


def test_model_partial_without_odds_can_reach_analyst_lean_confidence_band(tmp_path):
    features = {
        "leakage_status": "CLEAN",
        "table_available": True,
        "xg_available": True,
        "odds_available": False,
        "data_quality_score": 0.67,
        "xg_diff_edge_asof": 3.0,
        "home_recent_form_points_5": 10,
        "away_recent_form_points_5": 5,
    }
    result = run_v20_model_engine(features, tmp_path)
    assert result["model_status"] == "MODEL_PARTIAL"
    assert result["model_confidence"] >= 0.6
    assert "odds" in result["missing_inputs"]
