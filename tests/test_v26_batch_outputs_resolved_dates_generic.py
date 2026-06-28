import pandas as pd
from scripts.run_match_winner_batch import run_match_winner_batch
from tests.v25_test_helpers import fake_core_result


def test_v26_batch_outputs_resolved_dates_generic(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.resolve_fixture_date", lambda *a, **k: {"resolver_status": "RESOLVED", "match_date": "2026-03-01", "source_used": "v22_corpus", "candidates_count": 1, "reason": "ok", "reversed_fixture_found": False, "alias_matched": False, "candidates": []})
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    path = tmp_path / "batch.csv"
    pd.DataFrame([{"competition": "Premier League", "season": "2025/26", "match_date": "", "home_team": "Arsenal", "away_team": "Chelsea"}]).to_csv(path, index=False)
    result = run_match_winner_batch(input=str(path), output_dir=str(tmp_path / "out"))
    frame = pd.read_csv(result["winner_batch_results_csv_path"])
    assert frame.loc[0, "resolved_match_date"] == "2026-03-01"
    assert "as_of_date" in frame.columns

