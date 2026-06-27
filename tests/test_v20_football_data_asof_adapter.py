# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_football_data_asof_adapter import build_football_data_asof
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
ROOT=Path(__file__).resolve().parents[1]; FIX=ROOT/"tests/fixtures/v20_historical_internet_prediction"
def test_football_data_asof_excludes_future_match_and_builds_table(tmp_path):
    c=resolve_analysis_cutoff(build_match_context("Demo Home","Demo Away","Demo League","2025/26","2026-02-14"))
    r=build_football_data_asof(FIX/"football_data_matches_mock.csv",c,tmp_path)
    table=pd.read_csv(r["football_data_asof_table_path"])
    assert r["matches_used"]==4
    assert "Demo Home" in set(table["team"])
