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


if __name__ == "__main__":
    run_all()
