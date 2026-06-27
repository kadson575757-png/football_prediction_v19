# -*- coding: utf-8 -*-
from football_prediction_v19.analysis.v20_api_key_loader import load_v20_api_key_status
def test_api_key_loader_never_leaks_secret_values(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY","super_private_key_123")
    r=load_v20_api_key_status(["FOOTBALL_DATA_API_KEY"])
    assert r["keys"]["FOOTBALL_DATA_API_KEY"]["key_present"] is True
    assert "super_private_key_123" not in str(r)
    assert r["secrets_logged"] is False
