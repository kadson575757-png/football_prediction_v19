"""Local no-internet smoke test for the compare-models command."""
from __future__ import annotations

from football_prediction_v19.cli import main


def run_compare_models() -> None:
    main([
        "compare-models",
        "--input", "data/sample_matches.csv",
        "--output-dir", "outputs/model_comparison",
        "--test-season", "2023",
    ])


if __name__ == "__main__":
    run_compare_models()
