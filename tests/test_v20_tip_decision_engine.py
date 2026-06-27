# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine
def test_tip_engine_returns_tip_no_bet_and_data_blocked(tmp_path):
    model={"model_status":"MODEL_READY","home_win_probability":.5,"draw_probability":.25,"away_win_probability":.25,"model_confidence":.8,"model_risk_score":.2}
    good=run_tip_decision_engine(model,"ASOF_READY",{"data_quality_score":1,"odds_available":True},tmp_path/"good")
    low=run_tip_decision_engine(model,"ASOF_READY",{"data_quality_score":.2,"odds_available":True},tmp_path/"low")
    blocked=run_tip_decision_engine({"model_status":"MODEL_BLOCKED"},"ASOF_BLOCKED",{"data_quality_score":1},tmp_path/"blocked")
    assert good["decision_class"] in {"MODEL_TIP","ANALYST_LEAN"}
    assert low["decision_class"]=="NO_BET"
    assert blocked["decision_class"]=="DATA_BLOCKED"
