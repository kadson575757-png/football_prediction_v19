"""Run a local smoke pipeline with odds import — no live internet required."""
from __future__ import annotations

from football_prediction_v19.cli import main


def run_with_odds() -> None:
    main([
        "run-pipeline",
        "--skip-download",
        "--combine-output", "data/sample_matches.csv",
        "--fixtures-raw", "data/raw/upcoming_fixtures_raw_template.csv",
        "--fixtures-output", "data/upcoming_fixtures_odds.csv",
        "--fixtures-format", "native",
        "--model", "models/sample_odds_pipeline_model.joblib",
        "--predictions", "outputs/pipeline_predictions_with_odds.csv",
        "--excel", "outputs/pipeline_predictions_with_odds_report.xlsx",
        "--odds-raw", "data/raw/odds_raw_template.csv",
        "--odds-clean", "data/processed/odds_clean.csv",
        "--fixtures-with-odds", "data/upcoming_fixtures_with_odds.csv",
    ])


if __name__ == "__main__":
    run_with_odds()
