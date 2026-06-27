from football_prediction_v19.analysis.v20_understat_live_adapter import extract_understat_json_from_html


def test_v202_understat_escaped_json_parse():
    html = r"""<script>var datesData = JSON.parse('[{\"id\":\"7\",\"date\":\"2025-08-23\",\"h\":{\"title\":\"Arsenal\"},\"a\":{\"title\":\"Leeds\"},\"xG\":{\"h\":\"1.9\",\"a\":\"0.7\"}}]');</script>"""
    payload = extract_understat_json_from_html(html)
    assert payload[0]["id"] == "7"
