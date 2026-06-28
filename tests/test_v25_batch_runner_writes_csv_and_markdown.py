import pandas as pd
from pathlib import Path
from scripts.run_match_winner_batch import run_match_winner_batch
from tests.v25_test_helpers import fake_core_result


def test_v25_batch_runner_writes_csv_and_markdown(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    path = tmp_path / "batch.csv"
    pd.DataFrame([{"competition": "Premier League", "season": "2025/26", "match_date": "2026-02-14", "home_team": "Arsenal", "away_team": "Chelsea"}]).to_csv(path, index=False)
    result = run_match_winner_batch(input=str(path), output_dir=str(tmp_path / "out"))
    assert Path(result["winner_batch_results_csv_path"]).exists()
    assert Path(result["winner_batch_report_path"]).exists()

