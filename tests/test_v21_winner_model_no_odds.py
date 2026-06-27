from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v21_winner_model_no_odds(tmp_path):
    result = run_winner_model_core({"home_team": "A", "away_team": "B", "xg_missing": False, "odds_missing": True, "source_quality_score": 0.75}, {"eligibility_class": "WINNER_MODEL_READY"}, tmp_path)
    assert result["model_status"] == "WINNER_MODEL_READY"
    assert "odds" in result["missing_inputs"]
