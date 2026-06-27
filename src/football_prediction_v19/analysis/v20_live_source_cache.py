# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class CacheResult:
    cache_key: str
    cache_path: str
    cache_hit: bool
    cache_fresh: bool
    cache_age_hours: float | None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["warnings"] = list(self.warnings)
        return data


def build_cache_key(source_name: str, competition: str, season: str, endpoint_name: str, query: dict[str, Any] | str = "") -> str:
    query_text = json.dumps(query, sort_keys=True, default=str) if isinstance(query, dict) else str(query)
    digest = hashlib.sha256(query_text.encode("utf-8")).hexdigest()[:16]
    parts = [source_name, competition, season, endpoint_name, digest]
    return "__".join(_safe(p) for p in parts)


def read_cache(cache_dir: str | Path, cache_key: str, ttl_hours: float = 24) -> tuple[CacheResult, str]:
    path = Path(cache_dir) / f"{cache_key}.cache"
    if not path.exists():
        return CacheResult(cache_key, str(path.resolve()), False, False, None, ("cache miss",)), ""
    age = _age_hours(path)
    return CacheResult(cache_key, str(path.resolve()), True, age <= ttl_hours, round(age, 4), ()), path.read_text(encoding="utf-8")


def write_cache(cache_dir: str | Path, cache_key: str, payload: str) -> CacheResult:
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    target = path / f"{cache_key}.cache"
    target.write_text(_strip_secret_words(payload), encoding="utf-8")
    return CacheResult(cache_key, str(target.resolve()), True, True, 0.0, ())


def is_cache_fresh(cache_path: str | Path, ttl_hours: float = 24) -> bool:
    path = Path(cache_path)
    return path.exists() and _age_hours(path) <= ttl_hours


def get_cache_status(cache_dir: str | Path, cache_key: str, ttl_hours: float = 24) -> CacheResult:
    return read_cache(cache_dir, cache_key, ttl_hours)[0]


def _age_hours(path: Path) -> float:
    return (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 3600


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())[:80]


def _strip_secret_words(payload: str) -> str:
    text = str(payload)
    for marker in ["api_key=", "apikey=", "key="]:
        text = text.replace(marker, "redacted_")
    return text
