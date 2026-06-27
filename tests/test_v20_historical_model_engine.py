# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_historical_model_engine import run_v20_model_engine
def test_model_engine_outputs_probabilities_and_confidence_penalty(tmp_path):
    f={"leakage_status":"CLEAN","home_odds_implied_probability_asof":.45,"draw_odds_implied_probability_asof":.28,"away_odds_implied_probability_asof":.27,"xg_diff_edge_asof":1,"home_recent_form_points_5":6,"away_recent_form_points_5":4,"data_quality_score":1}
    r=run_v20_model_engine(f,tmp_path)
    assert r["model_status"]=="MODEL_READY"
    assert 0<=r["home_win_probability"]<=1
    assert r["model_confidence"]>0.7
