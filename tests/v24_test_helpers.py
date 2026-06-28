from pathlib import Path

import pandas as pd

from tests.v23_test_helpers import make_results_only_corpus
from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def make_prediction_results(path: Path) -> Path:
    rows = [
        {"match_id": "m1", "competition": "Premier League", "season": "2025/26", "match_date": "2025-08-01", "home_team": "A", "away_team": "B", "actual_result": "H", "decision_class": "NO_DECISION", "predicted_winner": "HOME", "home_win_probability": 0.40, "draw_probability": 0.32, "away_win_probability": 0.28, "confidence": 0.50, "source_quality_band": "MEDIUM", "eligibility_class": "LEAN_ONLY", "model_status": "WINNER_MODEL_PARTIAL", "prediction_tier": "TIER_2_RESULTS_ONLY", "xg_available": False, "odds_available": False, "early_season_risk": False},
        {"match_id": "m2", "competition": "Premier League", "season": "2025/26", "match_date": "2025-08-02", "home_team": "C", "away_team": "D", "actual_result": "A", "decision_class": "WINNER_LEAN", "predicted_winner": "AWAY", "home_win_probability": 0.25, "draw_probability": 0.30, "away_win_probability": 0.45, "confidence": 0.60, "source_quality_band": "MEDIUM", "eligibility_class": "LEAN_ONLY", "model_status": "WINNER_MODEL_PARTIAL", "prediction_tier": "TIER_2_RESULTS_ONLY", "xg_available": False, "odds_available": False, "early_season_risk": False},
        {"match_id": "m3", "competition": "Serie A", "season": "2025/26", "match_date": "2025-08-03", "home_team": "E", "away_team": "F", "actual_result": "D", "decision_class": "NO_DECISION", "predicted_winner": "DRAW", "home_win_probability": 0.34, "draw_probability": 0.35, "away_win_probability": 0.31, "confidence": 0.46, "source_quality_band": "LOW", "eligibility_class": "LEAN_ONLY", "model_status": "WINNER_MODEL_PARTIAL", "prediction_tier": "TIER_2_RESULTS_ONLY", "xg_available": False, "odds_available": True, "early_season_risk": True},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def run_v24_backtest(tmp_path: Path) -> dict[str, object]:
    corpus = make_results_only_corpus(tmp_path / "corpus.csv", n=12)
    return run_v21_winner_backtest(None, tmp_path / "out", corpus_path=corpus, max_matches=10, min_matches_required=2, decision_policy_config="config/v24_winner_decision_policy.yaml", emit_calibration_diagnostics=True, emit_threshold_simulation=True)
