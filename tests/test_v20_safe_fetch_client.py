# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_safe_fetch_client import SafeFetchClient
def test_safe_fetch_client_blocks_network_without_flag(tmp_path):
    r=SafeFetchClient(tmp_path, enable_network=False).fetch("source","endpoint","https://example.invalid")
    assert r.status=="DISABLED_NETWORK"
    assert r.network_used is False
