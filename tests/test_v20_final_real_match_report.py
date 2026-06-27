from football_prediction_v19.analysis.v20_final_real_match_report import write_v20_final_real_match_report


def test_final_real_match_report_sections_and_safety(tmp_path):
    path = write_v20_final_real_match_report({"match_context": {"home_team": "H", "away_team": "A", "match_date": "2026-02-14", "competition": "L", "season": "S"}, "decision_class": "NO_BET", "primary_tip": "NO_BET", "automatic_betting_enabled": False}, tmp_path)
    text = open(path, encoding="utf-8").read()
    assert "Fixture Resolution" in text
    assert "Final Tip Card" in text
    assert "No automatic betting. No stake. No ROI." in text
