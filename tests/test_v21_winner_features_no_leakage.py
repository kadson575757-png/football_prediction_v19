from football_prediction_v19.analysis.v21_winner_feature_store import build_winner_feature_store


def test_v21_winner_features_no_leakage(tmp_path):
    result = build_winner_feature_store({"canonical_match_id": "m1", "home_team": "A", "away_team": "B", "match_date": "2025-08-23"}, {"leakage_status": "CLEAN", "xg_available": True, "odds_available": False}, {"eligibility_class": "WINNER_MODEL_READY"}, {"source_quality_score": 0.7, "source_quality_band": "MEDIUM"}, tmp_path)
    assert result["features"]["leakage_status"] == "CLEAN"
