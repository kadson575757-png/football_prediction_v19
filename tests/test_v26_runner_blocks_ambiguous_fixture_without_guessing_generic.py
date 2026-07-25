from scripts.run_match_winner_analysis import run_match_winner_analysis


def test_v26_runner_blocks_ambiguous_fixture_without_guessing_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.resolve_fixture_date", lambda *a, **k: {"resolver_status": "AMBIGUOUS", "match_date": "", "source_used": "v22_corpus", "candidates_count": 2, "reason": "ambiguous", "reversed_fixture_found": False, "alias_matched": False, "candidates": [{"match_date": "x"}]})
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", output_dir=tmp_path)
    assert result["decision_class"] == "PROBABILITY_ONLY"
    assert result["fixture_resolver_status"] == "AMBIGUOUS"
    assert result["fixture_candidates_count"] == 2
    assert result["match_date"] == ""
    assert result["resolved_match_date"] == ""
    assert result["resolver_reason"] == "ambiguous"
    assert result["probability_model_status"] == "READY_WITH_LIMITATIONS"
    assert abs(sum(result[key] for key in ("home_win_probability", "draw_probability", "away_win_probability")) - 1.0) <= 1e-12

