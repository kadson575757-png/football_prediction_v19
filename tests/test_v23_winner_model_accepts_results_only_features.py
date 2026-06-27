from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v23_winner_model_accepts_results_only_features(tmp_path):
    model = run_winner_model_core({"form_edge": 8, "goals_for_edge": 6, "goals_against_edge": 4, "xg_missing": True, "odds_missing": True, "league_prediction_tier": "TIER_2_RESULTS_ONLY", "source_quality_score": 0.5}, {"eligibility_class": "LEAN_ONLY"}, tmp_path)
    assert model["model_status"] == "WINNER_MODEL_PARTIAL"
    assert model["home_win_probability"] > 0

