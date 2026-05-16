from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def _default_alias_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "team_aliases.json"


def _key(name: object) -> str:
    return " ".join(str(name).strip().split()).casefold()


@lru_cache(maxsize=1)
def load_team_aliases() -> dict[str, str]:
    path = _default_alias_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    aliases: dict[str, str] = {}
    for canonical, variants in data.items():
        canonical_clean = " ".join(str(canonical).strip().split())
        aliases[_key(canonical_clean)] = canonical_clean
        for variant in variants:
            aliases[_key(variant)] = canonical_clean
    return aliases


def normalize_team_name(name: str) -> str:
    cleaned = " ".join(str(name).strip().split())
    if not cleaned:
        return "Unknown"
    return load_team_aliases().get(_key(cleaned), cleaned)
