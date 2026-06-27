# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_odds_asof_adapter import build_odds_asof
ROOT=Path(__file__).resolve().parents[1]; FIX=ROOT/"tests/fixtures/v20_historical_internet_prediction"
def test_odds_asof_excludes_after_cutoff_and_computes_implied(tmp_path):
    c=resolve_analysis_cutoff(build_match_context("Demo Home","Demo Away","Demo League","2025/26","2026-02-14"))
    r=build_odds_asof(FIX/"historical_odds_mock.csv",FIX/"historical_totals_odds_mock.csv",c,tmp_path)
    clean=pd.read_csv(r["odds_asof_clean_path"]); excl=pd.read_csv(r["odds_asof_excluded_path"])
    assert r["odds_1x2_available"] is True
    assert clean["implied_probability"].between(0,1).all()
    assert len(excl)>=1
