from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v21_winner_probabilities_sum(tmp_path):
    result = run_winner_model_core({"home_team": "A", "away_team": "B", "source_quality_score": 0.7, "xg_missing": False}, {"eligibility_class": "WINNER_MODEL_READY"}, tmp_path)
    total = result["home_win_probability"] + result["draw_probability"] + result["away_win_probability"]
    assert abs(total - 1.0) < 0.01
