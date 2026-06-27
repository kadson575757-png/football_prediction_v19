# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
def test_historical_match_context_builds_generic_match_id():
    c=build_match_context("Home","Away","League","2025/26","2026-02-14")
    assert c.home_team=="Home"
    assert "home_away" in c.match_id
