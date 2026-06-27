from pathlib import Path

from football_prediction_v19.analysis.v21_winner_feature_store import build_winner_feature_store


def test_v21_winner_feature_store(tmp_path):
    result = build_winner_feature_store({"canonical_match_id": "m1", "home_team": "Arsenal", "away_team": "Leeds", "match_date": "2025-08-23", "prediction_tier": "TIER_1_FULL_XG"}, _features(), {"eligibility_class": "WINNER_MODEL_READY"}, {"source_quality_score": 0.7, "source_quality_band": "MEDIUM"}, tmp_path)
    assert result["features"]["form_edge"] > 0
    assert Path(result["winner_feature_store_csv_path"]).exists()


def _features():
    return {"home_recent_form_points_5": 10, "away_recent_form_points_5": 5, "home_recent_goals_for_5": 8, "away_recent_goals_for_5": 4, "home_recent_goals_against_5": 3, "away_recent_goals_against_5": 6, "home_xg_for_asof": 10, "away_xg_for_asof": 5, "xg_diff_edge_asof": 3, "home_rolling_xg_5": 7, "away_rolling_xg_5": 4, "xg_available": True, "odds_available": False, "leakage_status": "CLEAN"}
