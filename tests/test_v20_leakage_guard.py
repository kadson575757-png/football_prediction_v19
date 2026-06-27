# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_leakage_guard import SourceSnapshot, run_leakage_guard
def test_leakage_guard_blocks_critical_after_cutoff(tmp_path):
    c=resolve_analysis_cutoff(build_match_context("H","A","L","S","2026-02-14"))
    r=run_leakage_guard(c,[SourceSnapshot("future","odds","2026-02-15",1,True)],tmp_path)
    assert r["leakage_status"]=="BLOCKED"
    assert r["excluded_sources"]==1
