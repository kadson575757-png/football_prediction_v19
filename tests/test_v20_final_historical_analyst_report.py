# -*- coding: utf-8 -*-
from pathlib import Path
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_final_historical_analyst_report import write_final_historical_analyst_report
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
def test_final_report_contains_tip_no_bet_and_safety(tmp_path):
    c=resolve_analysis_cutoff(build_match_context("H","A","L","S","2026-02-14"))
    path=write_final_historical_analyst_report(c,{"leakage_status":"CLEAN"},{"table_available":True,"xg_available":True,"odds_1x2_available":True},{},{"home_win_probability":.4,"draw_probability":.3,"away_win_probability":.3},{"decision_class":"MODEL_TIP","primary_tip":"1X2_HOME"},tmp_path)
    text=Path(path).read_text(encoding="utf-8")
    assert "Final Tip Card" in text
    assert "No-Bet List" in text
    assert "No automatic betting" in text
