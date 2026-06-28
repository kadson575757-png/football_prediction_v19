from scripts.run_match_winner_analysis import run_match_winner_analysis


def test_v26_runner_blocks_ambiguous_fixture_without_guessing_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.resolve_fixture_date", lambda *a, **k: {"resolver_status": "AMBIGUOUS", "match_date": "", "source_used": "v22_corpus", "candidates_count": 2, "reason": "ambiguous", "reversed_fixture_found": False, "alias_matched": False, "candidates": [{"match_date": "x"}]})
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", output_dir=tmp_path)
    assert result["decision_class"] == "DATA_BLOCKED"
    assert result["fixture_candidates_count"] == 2

