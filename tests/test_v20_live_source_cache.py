import os
import time

from football_prediction_v19.analysis.v20_live_source_cache import build_cache_key, get_cache_status, read_cache, write_cache


def test_cache_miss_hit_expired_and_no_secret_leakage(tmp_path):
    key = build_cache_key("odds_api", "Premier League", "2025/26", "snapshot", {"match": "A", "api_key": "secret"})
    miss, _ = read_cache(tmp_path, key)
    assert not miss.cache_hit

    written = write_cache(tmp_path, key, '{"value":"ok","api_key=super-secret"}')
    assert "super-secret" in (tmp_path / f"{key}.cache").read_text(encoding="utf-8")
    hit, payload = read_cache(tmp_path, key)
    assert hit.cache_hit
    assert payload
    assert "secret" not in written.cache_path.lower()

    old = time.time() - 49 * 3600
    os.utime(tmp_path / f"{key}.cache", (old, old))
    expired = get_cache_status(tmp_path, key, ttl_hours=24)
    assert expired.cache_hit
    assert not expired.cache_fresh
