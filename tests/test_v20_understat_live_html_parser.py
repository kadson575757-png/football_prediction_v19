from football_prediction_v19.analysis.v20_understat_live_adapter import extract_understat_json_from_html, normalize_understat_matches, parse_understat_dates


def test_extracts_understat_datesdata_json_parse_html():
    html = r"<script>var datesData = JSON.parse('[{\"id\":\"1\",\"datetime\":\"2025-08-16 15:00:00\",\"h\":{\"title\":\"Arsenal\"},\"a\":{\"title\":\"Chelsea\"},\"xG\":{\"h\":\"1.7\",\"a\":\"1.1\"}}]');</script>"
    payload = extract_understat_json_from_html(html)
    frame = normalize_understat_matches(payload)
    assert len(frame) == 1
    assert frame.loc[0, "home_team"] == "Arsenal"
    assert frame.loc[0, "away_xg"] == 1.1


def test_parse_understat_dates_normalizes_to_iso():
    dates = parse_understat_dates(["2025-08-16 15:00:00"])
    assert dates.iloc[0] == "2025-08-16"
