import pandas as pd
from scripts.run_match_winner_batch import run_match_winner_batch


def test_v26_batch_does_not_guess_ambiguous_dates_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.resolve_fixture_date", lambda *a, **k: {"resolver_status": "AMBIGUOUS", "match_date": "", "source_used": "v22_corpus", "candidates_count": 2, "reason": "ambiguous", "reversed_fixture_found": False, "alias_matched": False, "candidates": []})
    path = tmp_path / "batch.csv"
    pd.DataFrame([{"competition": "Premier League", "season": "2025/26", "match_date": "", "home_team": "Arsenal", "away_team": "Chelsea"}]).to_csv(path, index=False)
    result = run_match_winner_batch(input=str(path), output_dir=str(tmp_path / "out"))
    frame = pd.read_csv(result["winner_batch_results_csv_path"])
    assert frame.loc[0, "decision_class"] == "DATA_BLOCKED"

