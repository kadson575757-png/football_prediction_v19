# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class FetchResult:
    source_name: str
    endpoint_name: str
    status: str
    network_used: bool
    cache_used: bool
    cache_path: str
    records_count: int = 0
    warnings: str = ""
    errors: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SafeFetchClient:
    def __init__(self, cache_dir: str | Path, *, enable_network: bool = False, rate_limit_seconds: float = 2.0) -> None:
        self.cache_dir = Path(cache_dir); self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enable_network = enable_network
        self.rate_limit_seconds = rate_limit_seconds

    def fetch(self, source_name: str, endpoint_name: str, url: str = "", *, requires_api_key: bool = False, key_present: bool = True) -> FetchResult:
        cache_path = self.cache_dir / f"{source_name}_{endpoint_name}.cache"
        if cache_path.exists():
            return FetchResult(source_name, endpoint_name, "CACHE_HIT", False, True, str(cache_path), 1)
        if not self.enable_network:
            return FetchResult(source_name, endpoint_name, "DISABLED_NETWORK", False, False, str(cache_path), warnings="network disabled")
        if requires_api_key and not key_present:
            return FetchResult(source_name, endpoint_name, "DISABLED_MISSING_KEY", False, False, str(cache_path), errors="missing api key")
        cache_path.write_text("", encoding="utf-8")
        return FetchResult(source_name, endpoint_name, "SUCCESS", True, False, str(cache_path), 0)
