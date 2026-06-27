from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v23_winner_model_confidence_cap_without_xg(tmp_path):
    model = run_winner_model_core({"form_edge": 20, "goals_for_edge": 20, "xg_missing": True, "odds_missing": False, "league_prediction_tier": "TIER_2_RESULTS_ONLY", "source_quality_score": 1}, {"eligibility_class": "LEAN_ONLY"}, tmp_path)
    assert model["confidence"] <= 0.62

