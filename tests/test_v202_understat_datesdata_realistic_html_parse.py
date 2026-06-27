from football_prediction_v19.analysis.v20_understat_live_adapter import parse_understat_dates_data, normalize_understat_matches


def test_v202_understat_datesdata_realistic_html_parse():
    html = """
    <html><script>
    var datesData = JSON.parse('[{\"id\":\"100\",\"datetime\":\"2025-08-22 20:00:00\",\"h\":{\"title\":\"Arsenal\"},\"a\":{\"title\":\"Leeds\"},\"xG\":{\"h\":\"2.02\",\"a\":\"0.81\"}}]');
    </script></html>
    """
    payload, pattern = parse_understat_dates_data(html)
    frame = normalize_understat_matches(payload)
    assert pattern == "datesdata_json_parse_single_quoted"
    assert frame.loc[0, "home_team"] == "Arsenal"
    assert frame.loc[0, "away_team"] == "Leeds United"
