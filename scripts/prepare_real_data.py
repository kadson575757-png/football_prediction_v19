from __future__ import annotations

from football_prediction_v19.cli import main


if __name__ == "__main__":
    main(
        [
            "prepare-data",
            "--input",
            "data/raw/real_matches.csv",
            "--output",
            "data/processed/real_matches_clean.csv",
            "--format",
            "auto",
        ]
    )
