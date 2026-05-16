"""Run a local smoke pipeline using sample/template data — no live internet required."""
from __future__ import annotations

from football_prediction_v19.cli import main


def run_pipeline() -> None:
    main([
        "run-pipeline",
        "--skip-download",
        "--combine-output", "data/sample_matches.csv",
        "--fixtures-raw", "data/raw/upcoming_fixtures_raw_template.csv",
        "--fixtures-output", "data/upcoming_fixtures.csv",
        "--fixtures-format", "native",
        "--model", "models/sample_pipeline_model.joblib",
        "--predictions", "outputs/pipeline_predictions.csv",
        "--excel", "outputs/pipeline_predictions_report.xlsx",
        "--backtest-csv", "outputs/pipeline_backtest_bets.csv",
        "--backtest-report", "outputs/pipeline_backtest_report.md",
        "--test-season", "2023",
    ])


if __name__ == "__main__":
    run_pipeline()
