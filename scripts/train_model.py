from football_prediction_v19.cli import main

if __name__ == "__main__":
    main(["train", "--input", "data/sample_matches.csv", "--model", "models/sample_model.joblib", "--test-season", "2023"])
