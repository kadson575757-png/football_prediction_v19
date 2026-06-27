# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
def test_cutoff_policies_resolve_match_start_and_kickoff_minus_one():
    c=resolve_analysis_cutoff(build_match_context("H","A","L","S","2026-02-14"))
    k=resolve_analysis_cutoff(build_match_context("H","A","L","S","2026-02-14", kickoff_time="20:30", cutoff_policy="KICKOFF_MINUS_1_MINUTE"))
    assert c.analysis_cutoff=="2026-02-14 00:00:00"
    assert k.analysis_cutoff=="2026-02-14 20:29:00"
