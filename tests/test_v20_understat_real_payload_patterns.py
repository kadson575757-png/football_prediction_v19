from football_prediction_v19.analysis.v20_understat_live_adapter import extract_understat_json_from_html, normalize_understat_matches


def test_plain_matches_payload_pattern_normalizes():
    payload = {"matches": [{"date": "2025-08-16", "home_team": "Lazio", "away_team": "Atalanta", "home_xg": "1.2", "away_xg": "1.6"}]}
    frame = normalize_understat_matches(payload)
    assert frame.loc[0, "home_xg"] == 1.2


def test_inline_datesdata_array_pattern_normalizes():
    html = '<script>var datesData = [{"id":"2","date":"2025-08-17","h":{"title":"Bayern Munich"},"a":{"title":"Borussia Dortmund"},"xG":{"h":"2.1","a":"1.4"}}];</script>'
    frame = normalize_understat_matches(extract_understat_json_from_html(html))
    assert frame.loc[0, "away_team"] == "Borussia Dortmund"
