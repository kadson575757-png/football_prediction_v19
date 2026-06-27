# -*- coding: utf-8 -*-
from pathlib import Path
from scripts.run_v20_historical_internet_prediction import run_v20_historical_internet_prediction
ROOT=Path(__file__).resolve().parents[1]; FIX=ROOT/"tests/fixtures/v20_historical_internet_prediction"
def test_one_command_runner_creates_complete_output(tmp_path):
    r=run_v20_historical_internet_prediction(home_team="Demo Home",away_team="Demo Away",competition="Demo League",season="2025/26",match_date="2026-02-14",cutoff_policy="MATCH_DATE_START",mock_data_dir=FIX,output_dir=tmp_path,base_dir=ROOT)
    assert r["v20_historical_internet_prediction_status"]=="V20_HISTORICAL_INTERNET_PREDICTION_READY"
    assert r["asof_status"]=="ASOF_READY"
    assert Path(r["v20_historical_internet_prediction_result_json_path"]).exists()
    assert Path(tmp_path/"v20_tip_decision_card.md").exists()
