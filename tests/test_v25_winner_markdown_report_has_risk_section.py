from football_prediction_v19.analysis.v25_winner_report import render_winner_markdown_report


def test_v25_winner_markdown_report_has_risk_section():
    text = render_winner_markdown_report({"home_team": "Arsenal", "away_team": "Chelsea", "risk_notes": ["xG missing"]})
    assert "## Risiken" in text
    assert "xG missing" in text
