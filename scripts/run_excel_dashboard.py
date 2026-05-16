"""Local no-internet smoke test for the Excel dashboard export.

Creates minimal sample files for model comparison, metadata, and backtest,
then exports a full Excel dashboard.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

from football_prediction_v19.cli import main


def _make_sample_model_comparison(path: Path) -> None:
    df = pd.DataFrame([
        {
            "model_name": "random_forest", "calibrated": True,
            "accuracy": 0.54, "balanced_accuracy": 0.51,
            "log_loss": 0.97, "brier_score": 0.62,
            "avg_confidence": 0.55, "avg_correct_confidence": 0.58,
            "train_rows": 240, "test_rows": 40,
            "feature_count": 32, "selected_as_best": True, "warnings": "",
        },
        {
            "model_name": "logistic_regression", "calibrated": False,
            "accuracy": 0.50, "balanced_accuracy": 0.49,
            "log_loss": 1.01, "brier_score": 0.65,
            "avg_confidence": 0.51, "avg_correct_confidence": 0.52,
            "train_rows": 240, "test_rows": 40,
            "feature_count": 32, "selected_as_best": False, "warnings": "",
        },
        {
            "model_name": "gradient_boosting", "calibrated": False,
            "accuracy": 0.52, "balanced_accuracy": 0.50,
            "log_loss": 0.99, "brier_score": 0.64,
            "avg_confidence": 0.77, "avg_correct_confidence": 0.55,
            "train_rows": 240, "test_rows": 40,
            "feature_count": 32, "selected_as_best": False,
            "warnings": "Overconfident: avg confidence 0.77 > 0.75",
        },
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _make_sample_metadata(path: Path) -> None:
    meta = {
        "model_name": "random_forest",
        "calibrated": True,
        "test_season": 2023,
        "selected_metric": "log_loss",
        "accuracy": 0.54,
        "log_loss": 0.97,
        "brier_score": 0.62,
        "feature_columns": ["home_form_xg", "away_form_xg", "odds_home", "odds_draw"],
        "training_rows": 240,
        "test_rows": 40,
        "created_at": "2025-01-01T00:00:00+00:00",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _make_sample_backtest(path: Path) -> None:
    df = pd.DataFrame([
        {
            "date": "2023-08-20", "home_team": "Arsenal", "away_team": "Chelsea",
            "value_pick": "H", "value_edge": 0.08, "odds_used": 2.10,
            "bet_recommendation": "Bet H", "bet_result": "win",
            "profit": 1.10, "cumulative_profit": 1.10,
            "no_bet_reasons": "",
        },
        {
            "date": "2023-08-20", "home_team": "Wolves", "away_team": "Man Utd",
            "value_pick": "A", "value_edge": 0.04, "odds_used": 3.20,
            "bet_recommendation": "No bet", "bet_result": "",
            "profit": 0.0, "cumulative_profit": 1.10,
            "no_bet_reasons": "Edge too low",
        },
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def run_excel_dashboard() -> None:
    root = Path(__file__).resolve().parents[1]
    predictions_path = root / "outputs" / "predictions.csv"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cmp_csv = tmp / "model_comparison.csv"
        meta_json = tmp / "best_model_metadata.json"
        bt_csv = tmp / "backtest_bets.csv"
        output_path = root / "outputs" / "predictions_dashboard.xlsx"

        _make_sample_model_comparison(cmp_csv)
        _make_sample_metadata(meta_json)
        _make_sample_backtest(bt_csv)

        if not predictions_path.exists():
            print("  No predictions.csv found — running pipeline first...")
            main([
                "run-pipeline",
                "--skip-download",
                "--combine-output", str(root / "data" / "sample_matches.csv"),
                "--fixtures-raw", str(root / "data" / "raw" / "upcoming_fixtures_raw_template.csv"),
                "--fixtures-output", str(root / "data" / "upcoming_fixtures_dashboard.csv"),
                "--model", str(tmp / "model.joblib"),
                "--predictions", str(predictions_path),
                "--excel", str(tmp / "basic_report.xlsx"),
                "--skip-backtest",
            ])

        main([
            "export-excel",
            "--predictions", str(predictions_path),
            "--output", str(output_path),
            "--model-comparison", str(cmp_csv),
            "--model-metadata", str(meta_json),
            "--backtest-csv", str(bt_csv),
        ])
        print(f"  Dashboard saved: {output_path}")


if __name__ == "__main__":
    run_excel_dashboard()
