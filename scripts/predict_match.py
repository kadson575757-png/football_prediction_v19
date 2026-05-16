from football_prediction_v19.cli import main

if __name__ == "__main__":
    main([
        "predict",
        "--history", "data/sample_matches.csv",
        "--model", "models/sample_model.joblib",
        "--home", "Chelsea",
        "--away", "Arsenal",
        "--date", "2024-05-01",
        "--venue", "Stamford Bridge",
        "--referee", "Anthony Taylor",
        "--odds-home", "2.40",
        "--odds-draw", "3.40",
        "--odds-away", "2.90",
    ])
