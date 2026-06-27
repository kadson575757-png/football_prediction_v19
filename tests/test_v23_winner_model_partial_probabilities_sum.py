from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v23_winner_model_partial_probabilities_sum(tmp_path):
    model = run_winner_model_core({"xg_missing": True, "odds_missing": True, "league_prediction_tier": "TIER_2_RESULTS_ONLY"}, {"eligibility_class": "LEAN_ONLY"}, tmp_path)
    total = model["home_win_probability"] + model["draw_probability"] + model["away_win_probability"]
    assert abs(total - 1.0) < 0.01

