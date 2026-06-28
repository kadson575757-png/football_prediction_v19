from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v26_asof_fields_in_runner_output_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-03-01", output_dir=tmp_path)
    assert result["as_of_date"] == "2026-02-28"
    assert result["asof_guard_status"] == "CLEAN"
