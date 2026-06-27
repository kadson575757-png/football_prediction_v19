# -*- coding: utf-8 -*-
from pathlib import Path
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from scripts.run_v20_historical_internet_prediction import run_v20_historical_internet_prediction
ROOT=Path(__file__).resolve().parents[1]; FIX=ROOT/"tests/fixtures/v20_historical_internet_prediction"
def test_feature_store_contains_asof_data_and_quality(tmp_path):
    r=run_v20_historical_internet_prediction(home_team="Demo Home",away_team="Demo Away",competition="Demo League",season="2025/26",match_date="2026-02-14",cutoff_policy="MATCH_DATE_START",mock_data_dir=FIX,output_dir=tmp_path,base_dir=ROOT)
    f=r["features"]
    assert f["leakage_status"]=="CLEAN"
    assert f["data_quality_score"]>=0.9
    assert "home_xg_for_asof" in f
