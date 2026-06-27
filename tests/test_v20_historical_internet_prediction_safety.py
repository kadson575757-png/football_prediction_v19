# -*- coding: utf-8 -*-
from pathlib import Path
from scripts.run_v20_historical_internet_prediction import run_v20_historical_internet_prediction
ROOT=Path(__file__).resolve().parents[1]; FIX=ROOT/"tests/fixtures/v20_historical_internet_prediction"
def test_runner_safety_flags_false_and_no_stake_roi(tmp_path):
    r=run_v20_historical_internet_prediction(home_team="Demo Home",away_team="Demo Away",competition="Demo League",season="2025/26",match_date="2026-02-14",cutoff_policy="MATCH_DATE_START",mock_data_dir=FIX,output_dir=tmp_path,base_dir=ROOT)
    assert r["network_calls_enabled"] is False
    assert r["automatic_betting_enabled"] is False
    assert r["staking_logic_enabled"] is False
    assert r["roi_logic_enabled"] is False
    text=Path(tmp_path/"v20_final_historical_analyst_report.md").read_text(encoding="utf-8").lower()
    assert "stake" in text and "roi" in text
    assert "money management" not in text
