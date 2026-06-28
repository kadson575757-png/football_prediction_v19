from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v25_runner_uses_safe_default_policy(monkeypatch, tmp_path):
    seen = {}
    def fake_core(**kwargs):
        seen.update(kwargs)
        return fake_core_result()
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", fake_core)
    run_match_winner_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-02-14", output_dir=tmp_path)
    assert "decision_policy_config" not in seen

