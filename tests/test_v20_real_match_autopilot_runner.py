from scripts.run_v20_real_match_autopilot import run_v20_real_match_autopilot


def test_real_match_autopilot_runner_ready_with_mock_sources(tmp_path):
    result = run_v20_real_match_autopilot(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_real_match_autopilot", output_dir=tmp_path, base_dir=".")
    assert result["v20_real_match_autopilot_status"] in {"READY", "PARTIAL"}
    assert result["fixture_resolution_status"] in {"RESOLVED", "PARTIAL"}
    assert result["source_readiness"] in {"READY_FOR_MODEL", "READY_FOR_ANALYST_LEAN"}
    assert result["automatic_betting_enabled"] is False
    assert (tmp_path / "v20_final_real_match_report.md").exists()
