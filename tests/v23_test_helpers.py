from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def make_results_only_corpus(path: Path, n: int = 12, *, missing_result: bool = False) -> Path:
    rows = []
    for i in range(n):
        result = "H" if i % 3 == 0 else ("A" if i % 3 == 1 else "D")
        rows.append(
            {
                "canonical_match_id": f"m{i}",
                "competition": "Premier League",
                "season": "2025/26",
                "match_date": f"2025-08-{i + 1:02d}",
                "home_team": f"Team {i % 4}",
                "away_team": f"Team {(i + 1) % 4}",
                "home_goals": 2 if result == "H" else (0 if result == "A" else 1),
                "away_goals": 0 if result == "H" else (2 if result == "A" else 1),
                "result_1x2": "" if missing_result and i == 0 else result,
                "result_available": not (missing_result and i == 0),
                "match_completed": True,
                "football_data_available": True,
                "understat_available": False,
                "xg_available": False,
                "home_xg": "",
                "away_xg": "",
                "home_xga": "",
                "away_xga": "",
                "odds_available": False,
                "prediction_tier": "TIER_2_RESULTS_ONLY",
                "source_quality_band": "LOW",
                "can_backtest": not (missing_result and i == 0),
                "cannot_backtest_reason": "result unavailable" if missing_result and i == 0 else "",
                "home_team_normalized": f"team{i % 4}",
                "away_team_normalized": f"team{(i + 1) % 4}",
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def run_results_only_backtest(tmp_path: Path, n: int = 12) -> dict[str, object]:
    corpus = make_results_only_corpus(tmp_path / "corpus.csv", n=n)
    return run_v21_winner_backtest(None, tmp_path / "out", corpus_path=corpus, max_matches=min(n, 10), min_matches_required=2)
