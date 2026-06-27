from football_prediction_v19.analysis.v20_real_match_autopilot_dashboard import write_v20_real_match_autopilot_dashboard


def test_real_match_autopilot_dashboard_written(tmp_path):
    path = write_v20_real_match_autopilot_dashboard({"v20_real_match_autopilot_status": "READY", "fixture_resolution_status": "RESOLVED", "source_readiness": "READY_FOR_MODEL", "source_quality_band": "HIGH", "decision_class": "MODEL_TIP", "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}, tmp_path)
    assert "READY" in open(path, encoding="utf-8").read()
