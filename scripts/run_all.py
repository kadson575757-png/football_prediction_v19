from __future__ import annotations

from football_prediction_v19.cli import main


def run_all() -> None:
    main(
        [
            "prepare-fixtures",
            "--input",
            "data/raw/upcoming_fixtures_raw_template.csv",
            "--output",
            "data/upcoming_fixtures.csv",
            "--format",
            "native",
        ]
    )
    main(
        [
            "import-football-data",
            "--input",
            "data/raw/football_data_template.csv",
            "--output",
            "data/processed/football_data_clean.csv",
        ]
    )
    main(
        [
            "train",
            "--input",
            "data/sample_matches.csv",
            "--model",
            "models/sample_model.joblib",
            "--test-season",
            "2023",
        ]
    )
    main(
        [
            "predict",
            "--history",
            "data/sample_matches.csv",
            "--model",
            "models/sample_model.joblib",
            "--home",
            "Chelsea",
            "--away",
            "Arsenal",
            "--date",
            "2024-05-01",
            "--venue",
            "Stamford Bridge",
            "--referee",
            "Anthony Taylor",
            "--odds-home",
            "2.40",
            "--odds-draw",
            "3.40",
            "--odds-away",
            "2.90",
        ]
    )
    main(
        [
            "predict-fixtures",
            "--history",
            "data/sample_matches.csv",
            "--fixtures",
            "data/upcoming_fixtures_template.csv",
            "--model",
            "models/sample_model.joblib",
            "--output",
            "outputs/predictions.csv",
        ]
    )
    main(
        [
            "export-excel",
            "--predictions",
            "outputs/predictions.csv",
            "--output",
            "outputs/predictions_report.xlsx",
        ]
    )


def run_pipeline_smoke() -> None:
    """Pipeline smoke test using local sample data — no internet required."""
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


def run_odds_smoke() -> None:
    """Odds import smoke test using local template data — no internet required."""
    main(["prepare-odds", "--input", "data/raw/odds_raw_template.csv",
          "--output", "data/processed/odds_clean.csv"])
    main([
        "merge-odds-fixtures",
        "--fixtures", "data/upcoming_fixtures.csv",
        "--odds", "data/processed/odds_clean.csv",
        "--output", "data/upcoming_fixtures_with_odds.csv",
    ])


def run_xg_smoke() -> None:
    """xG import smoke test using local template data — no internet required."""
    main(["prepare-xg", "--input", "data/raw/xg_raw_template.csv",
          "--output", "data/processed/xg_clean.csv"])
    main([
        "merge-xg-history",
        "--history", "data/sample_matches.csv",
        "--xg", "data/processed/xg_clean.csv",
        "--output", "data/processed/sample_matches_with_xg.csv",
    ])


def run_compare_models_smoke() -> None:
    """Model comparison smoke test using local sample data — no internet required."""
    main([
        "compare-models",
        "--input", "data/sample_matches.csv",
        "--output-dir", "outputs/model_comparison",
        "--test-season", "2023",
    ])


def run_excel_dashboard_smoke() -> None:
    """Excel dashboard smoke test using sample data — no internet required."""
    from scripts.run_excel_dashboard import run_excel_dashboard
    run_excel_dashboard()


if __name__ == "__main__":
    run_all()
    run_pipeline_smoke()
    run_odds_smoke()
    run_xg_smoke()
    run_compare_models_smoke()
