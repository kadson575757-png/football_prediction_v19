from football_prediction_v19.analysis.v20_final_real_match_report import write_v20_final_real_match_report


def test_final_report_explains_missing_odds_key(tmp_path):
    result = {
        "decision_class": "ANALYST_LEAN",
        "block_reasons": [],
        "source_status": {},
        "match_context": {"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2026-02-14", "competition": "Premier League", "season": "2025/26"},
        "odds_available": False,
    }
    path = write_v20_final_real_match_report(result, tmp_path)
    text = open(path, encoding="utf-8").read()
    assert "Odds unavailable because no API key was provided" in text
    assert "No automatic betting" in text
