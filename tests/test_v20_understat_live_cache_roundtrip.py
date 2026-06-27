from football_prediction_v19.analysis.v20_understat_live_adapter import read_understat_cache, write_understat_cache


def test_understat_cache_roundtrip(tmp_path):
    write = write_understat_cache(tmp_path, "understat_demo", '{"matches": []}')
    read, payload = read_understat_cache(tmp_path, "understat_demo")
    assert write["cache_hit"] is True
    assert read["cache_hit"] is True
    assert payload == '{"matches": []}'
