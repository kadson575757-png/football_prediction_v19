from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v21_winner_model_xg_confidence(tmp_path):
    with_xg = run_winner_model_core({"home_team": "A", "away_team": "B", "xg_missing": False, "source_quality_score": 0.75}, {"eligibility_class": "WINNER_MODEL_READY"}, tmp_path / "xg")
    no_xg = run_winner_model_core({"home_team": "A", "away_team": "B", "xg_missing": True, "source_quality_score": 0.75}, {"eligibility_class": "WINNER_MODEL_PARTIAL"}, tmp_path / "noxg")
    assert with_xg["confidence"] >= no_xg["confidence"]
