from football_prediction_v19.analysis.v20_understat_live_adapter import read_understat_cache, write_understat_cache


def test_v202_understat_cache_roundtrip_realistic(tmp_path):
    payload = "<html><script>var datesData = [];</script></html>"
    write_understat_cache(tmp_path, "epl_2025", payload)
    meta, cached = read_understat_cache(tmp_path, "epl_2025")
    assert meta["cache_hit"] is True
    assert cached == payload
