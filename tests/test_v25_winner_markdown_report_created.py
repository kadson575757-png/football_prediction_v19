from pathlib import Path
from football_prediction_v19.analysis.v25_winner_report import write_winner_report


def test_v25_winner_markdown_report_created(tmp_path):
    paths = write_winner_report({"home_team": "Arsenal", "away_team": "Chelsea", "decision_class": "NO_DECISION"}, tmp_path)
    assert Path(paths["winner_analysis_markdown_path"]).exists()

