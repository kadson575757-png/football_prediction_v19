from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v26_runner_outputs_resolver_fields_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.resolve_fixture_date", lambda *a, **k: {"resolver_status": "RESOLVED", "match_date": "2026-03-01", "source_used": "v22_corpus", "candidates_count": 1, "reason": "ok", "reversed_fixture_found": False, "alias_matched": False, "candidates": []})
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", output_dir=tmp_path)
    assert {"fixture_resolver_status", "fixture_resolver_source", "resolved_match_date", "resolver_reason"}.issubset(result)

