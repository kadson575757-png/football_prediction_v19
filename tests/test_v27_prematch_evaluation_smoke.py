import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v27_prematch_evaluation import run_prematch_evaluation


def test_v27_prematch_evaluation_smoke(monkeypatch, tmp_path):
    input_csv = tmp_path / "input.csv"
    pd.DataFrame(
        [
            {"competition": "Premier League", "season": "2025/26", "home_team": "Arsenal", "away_team": "Chelsea", "match_date": "", "expected_result_source": "mock"},
            {"competition": "Bundesliga", "season": "2025/26", "home_team": "Bayern Munich", "away_team": "Borussia Dortmund", "match_date": "2026-04-12", "expected_result_source": "mock"},
        ]
    ).to_csv(input_csv, index=False)

    def fake_runner(**kwargs):
        return {
            "winner_analysis_status": "READY",
            "match_date": kwargs.get("match_date") or "2026-03-01",
            "resolved_match_date": kwargs.get("match_date") or "2026-03-01",
            "as_of_date": "2026-02-28",
            "fixture_resolver_status": "RESOLVED",
            "fixture_resolver_source": "mock",
            "asof_guard_status": "CLEAN",
            "decision_class": "WINNER_LEAN",
            "predicted_winner": "HOME",
            "home_win_probability": 0.45,
            "draw_probability": 0.30,
            "away_win_probability": 0.25,
            "confidence": 0.55,
            "risk_level": "HIGH",
            "source_quality_band": "MEDIUM",
            "prediction_tier": "TIER_2_RESULTS_ONLY",
            "xg_available": False,
            "odds_available": False,
            "primary_reasons": ["home edge"],
            "risk_notes": ["mock risk"],
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        }

    monkeypatch.setattr("football_prediction_v19.analysis.v27_prematch_evaluation.run_match_winner_analysis", fake_runner)
    monkeypatch.setattr(
        "football_prediction_v19.analysis.v27_prematch_evaluation.resolve_match_result",
        lambda *args, **kwargs: {"result_status": "RESOLVED", "home_goals": 2, "away_goals": 1, "result": "HOME_WIN", "source_used": "mock", "reason": "ok"},
    )

    result = run_prematch_evaluation(input_csv, output_dir=tmp_path / "out")

    assert result["matches_requested"] == 2
    assert Path(result["v27_prematch_evaluation_rows_csv_path"]).exists()
    assert Path(result["v27_prematch_evaluation_summary_json_path"]).exists()
    assert Path(result["v27_prematch_evaluation_report_md_path"]).exists()
    summary = json.loads(Path(result["v27_prematch_evaluation_summary_json_path"]).read_text(encoding="utf-8"))
    assert summary["matches_requested"] == 2

