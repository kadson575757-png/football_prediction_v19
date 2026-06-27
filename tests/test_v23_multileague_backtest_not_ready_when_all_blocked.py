import pandas as pd

from scripts.run_v22_multileague_winner_backtest import run_v22_multileague_winner_backtest


def test_v23_multileague_backtest_not_ready_when_all_blocked(monkeypatch, tmp_path):
    def fake_backtest(*args, **kwargs):
        return {"corpus_status": "READY", "matches_requested": 10, "matches_available": 10, "matches_evaluated": 10, "winner_pick_count": 0, "winner_lean_count": 0, "no_clear_winner_count": 0, "no_decision_count": 0, "data_blocked_count": 10, "hard_data_blocked_count": 0, "non_hard_data_blocked_count": 10, "invalid_data_blocked_count": 10, "decision_attempt_count": 0, "model_ran_count": 0, "probabilities_created_count": 0, "no_xg_partial_model_count": 0, "odds_missing_non_block_count": 0, "understat_failed_non_block_count": 0, "top1_accuracy": 0.0, "brier_score_1x2": 0.0}
    monkeypatch.setattr("scripts.run_v22_multileague_winner_backtest.run_v21_winner_backtest", fake_backtest)
    result = run_v22_multileague_winner_backtest(season="2025/26", competitions="Premier League", output_dir=str(tmp_path))
    assert result["v22_multileague_backtest_status"] == "BLOCKING_BUG_DETECTED"

