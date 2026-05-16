from football_prediction_v19.cli import main

if __name__ == "__main__":
    main(["backtest", "--input", "data/sample_matches.csv", "--test-season", "2023"])
