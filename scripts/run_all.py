from __future__ import annotations

from football_prediction_v19.cli import main


def run_all() -> None:
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


if __name__ == "__main__":
    run_all()
