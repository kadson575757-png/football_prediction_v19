from pathlib import Path

from scripts.run_v21_predict_winners_batch import run_v21_predict_winners_batch


def test_v21_winner_batch_no_decision_report(tmp_path):
    run_v21_predict_winners_batch(competition="Premier League", season="2025/26", date="2026-02-15", mock_data_dir="tests/fixtures/v20_live_source_adapters", output_dir=str(tmp_path))
    assert Path(tmp_path / "v21_winner_batch_no_decision_report.md").exists()
