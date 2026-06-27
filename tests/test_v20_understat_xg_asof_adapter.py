# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_understat_xg_asof_adapter import build_understat_xg_asof
ROOT=Path(__file__).resolve().parents[1]; FIX=ROOT/"tests/fixtures/v20_historical_internet_prediction"
def test_understat_xg_asof_excludes_future_and_player_rows(tmp_path):
    c=resolve_analysis_cutoff(build_match_context("Demo Home","Demo Away","Demo League","2025/26","2026-02-14"))
    r=build_understat_xg_asof(FIX/"understat_xg_matches_mock.csv",FIX/"understat_player_xg_mock.csv",c,tmp_path)
    teams=pd.read_csv(r["understat_xg_asof_team_path"]); players=pd.read_csv(r["understat_xg_asof_player_path"])
    assert r["xg_available"] is True
    assert "Future Player" not in set(players["player"])
