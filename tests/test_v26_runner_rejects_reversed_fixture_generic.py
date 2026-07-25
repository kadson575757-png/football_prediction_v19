from scripts.run_match_winner_analysis import run_match_winner_analysis


def test_v26_runner_rejects_reversed_fixture_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.resolve_fixture_date", lambda *a, **k: {"resolver_status": "NOT_FOUND", "match_date": "", "source_used": "v22_corpus", "candidates_count": 0, "reason": "Only reversed fixture was found", "reversed_fixture_found": True, "alias_matched": False, "candidates": []})
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Chelsea", away="Arsenal", output_dir=tmp_path)
    assert result["decision_class"] == "PROBABILITY_ONLY"
    assert result["fixture_resolver_status"] == "NOT_FOUND"
    assert result["reversed_fixture_found"] is True
    assert result["home_team"] == "Chelsea"
    assert result["away_team"] == "Arsenal"
    assert result["match_date"] == ""
    assert result["resolved_match_date"] == ""
    assert result["resolver_reason"] == "Only reversed fixture was found"
    assert result["probability_model_status"] == "READY_WITH_LIMITATIONS"
    assert abs(sum(result[key] for key in ("home_win_probability", "draw_probability", "away_win_probability")) - 1.0) <= 1e-12

