import json

from scripts.run_v20_match import run_v20_match


def test_machine_result_contains_block_reasons_for_missing_fixture(tmp_path):
    result = run_v20_match(home_team="Unknown Home", away_team="Unknown Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_one_command_runner", output_dir=tmp_path, base_dir=".")
    machine = json.loads((tmp_path / "machine_result.json").read_text(encoding="utf-8"))
    for key in ["v20_match_status", "decision_class", "primary_tip", "source_quality_band", "source_quality_score", "fixture_resolution_status", "source_readiness", "asof_status", "leakage_status", "cache_used", "network_calls_enabled", "source_status", "missing_data", "block_reasons"]:
        assert key in machine
    assert machine["decision_class"] == "DATA_BLOCKED"
    assert "fixture_not_found" in machine["block_reasons"]
    assert machine["automatic_betting_enabled"] is False
