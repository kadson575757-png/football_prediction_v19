from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core


def test_v21_winner_model_core(tmp_path):
    result = run_winner_model_core(_features(), {"eligibility_class": "WINNER_MODEL_READY"}, tmp_path)
    assert result["model_status"] == "WINNER_MODEL_READY"
    assert result["predicted_winner"] in {"HOME", "DRAW", "AWAY", "NO_CLEAR_WINNER"}


def _features():
    return {"home_team": "Arsenal", "away_team": "Leeds", "form_edge": 5, "goals_for_edge": 4, "goals_against_edge": 3, "xg_diff_edge_asof": 4, "xg_momentum_edge": 2, "xg_defensive_edge": 1, "xg_missing": False, "odds_missing": True, "source_quality_score": 0.75, "source_quality_band": "MEDIUM", "league_prediction_tier": "TIER_1_FULL_XG"}
