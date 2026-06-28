from scripts.run_match_winner_analysis import run_match_winner_analysis


def test_v26_runner_rejects_reversed_fixture_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.resolve_fixture_date", lambda *a, **k: {"resolver_status": "NOT_FOUND", "match_date": "", "source_used": "v22_corpus", "candidates_count": 0, "reason": "Only reversed fixture was found", "reversed_fixture_found": True, "alias_matched": False, "candidates": []})
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Chelsea", away="Arsenal", output_dir=tmp_path)
    assert result["decision_class"] == "DATA_BLOCKED"
    assert result["reversed_fixture_found"] is True

