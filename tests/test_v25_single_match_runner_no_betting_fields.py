from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v25_single_match_runner_no_betting_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-02-14", output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False

