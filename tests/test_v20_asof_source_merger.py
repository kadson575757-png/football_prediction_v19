# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_asof_source_merger import merge_asof_sources
def test_asof_merger_builds_ready_coverage(tmp_path):
    r=merge_asof_sources({"table_available":True,"form_available":True},{"xg_available":True,"player_xg_available":True},{"odds_1x2_available":True,"odds_totals_available":True},{"leakage_status":"CLEAN"},tmp_path)
    assert r["asof_status"]=="ASOF_READY"
    assert r["leakage_clean"] is True
