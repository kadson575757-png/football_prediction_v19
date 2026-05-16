"""Run a local smoke pipeline with xG enrichment — no live internet required."""
from __future__ import annotations

from football_prediction_v19.cli import main


def run_with_xg() -> None:
    main([
        "run-pipeline",
        "--skip-download",
        "--combine-output", "data/sample_matches.csv",
        "--fixtures-raw", "data/raw/upcoming_fixtures_raw_template.csv",
        "--fixtures-output", "data/upcoming_fixtures_xg.csv",
        "--fixtures-format", "native",
        "--model", "models/sample_xg_pipeline_model.joblib",
        "--predictions", "outputs/pipeline_predictions_with_xg.csv",
        "--excel", "outputs/pipeline_predictions_with_xg_report.xlsx",
        "--xg-raw", "data/raw/xg_raw_template.csv",
        "--xg-clean", "data/processed/xg_clean.csv",
        "--history-with-xg", "data/processed/sample_matches_with_xg.csv",
    ])


if __name__ == "__main__":
    run_with_xg()
