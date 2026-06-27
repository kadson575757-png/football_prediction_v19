from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v23_winner_model_no_block_for_missing_odds(tmp_path):
    model = run_winner_model_core({"xg_missing": False, "odds_missing": True, "league_prediction_tier": "TIER_1_FULL_XG"}, {"eligibility_class": "WINNER_MODEL_READY"}, tmp_path)
    assert model["model_status"] != "WINNER_MODEL_BLOCKED"
    assert "odds" in model["missing_inputs"]
