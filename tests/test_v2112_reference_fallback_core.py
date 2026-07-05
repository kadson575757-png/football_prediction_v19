from scripts.analyze_v2112_exact_scoreline_pattern_test import choose_final_reference


def _stats(count):
    return {"reference_count": count, "home_wins": count, "draws": 0, "away_wins": 0, "home_rate": 1.0 if count else 0.0, "draw_rate": 0.0, "away_rate": 0.0, "top_outcome": "HOME" if count else "NO_REFERENCE", "tie_breaker": "NONE"}


def test_v2112_reference_fallback_priority():
    refs = {"exact_pair": _stats(1), "combined_single": _stats(2), "home_single": _stats(3), "away_single": _stats(4)}
    assert choose_final_reference(refs)["source"] == "EXACT_PAIR"

    refs["exact_pair"] = _stats(0)
    assert choose_final_reference(refs)["source"] == "COMBINED_SINGLE"

    refs["combined_single"] = _stats(0)
    assert choose_final_reference(refs)["source"] == "HOME_SINGLE"

    refs["home_single"] = _stats(0)
    assert choose_final_reference(refs)["source"] == "AWAY_SINGLE"

    refs["away_single"] = _stats(0)
    assert choose_final_reference(refs)["source"] == "NO_REFERENCE"

