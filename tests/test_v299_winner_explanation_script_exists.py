from pathlib import Path

from scripts.generate_v299_winner_explanation_report import generate_winner_explanation_report


def test_v299_winner_explanation_script_exists():
    assert Path("scripts/generate_v299_winner_explanation_report.py").exists()
    assert callable(generate_winner_explanation_report)
