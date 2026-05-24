from __future__ import annotations

import json
import re
import unicodedata
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


# ---------------------------------------------------------------------------
# Fuzzy key for fallback matching
# ---------------------------------------------------------------------------

#: Non-distinctive tokens stripped during fuzzy matching.
#: Only syntactic qualifiers — never meaningful name parts like "real", "atletico".
_FUZZY_STRIP: frozenset[str] = frozenset({
    # Club-type suffixes/prefixes (English)
    "fc", "afc", "cf", "cd", "rc", "rcd", "sc", "sv", "bv", "ud", "ca",
    "fk", "sk", "ac", "as", "ss", "us", "ik", "bk", "fv", "sbv", "nv",
    # Generic words
    "club", "football", "futbol",
    # Spanish prepositions (only safe in this context — no English club uses "de")
    "de", "del",
})


def fuzzy_team_key(name: str) -> str:
    """Return a normalised key for fuzzy team-name comparison.

    Used as a *fallback* when ``normalize_team_name`` does not produce an
    exact match.  The key is intentionally lossy — it strips common
    prefixes/suffixes ("FC", "AFC", "de", etc.) and removes accents.

    Safety guarantee: accepts a match only when a single unambiguous candidate
    remains (enforced at call-site, not here).

    Steps
    -----
    1. Apply ``normalize_team_name`` (alias lookup).
    2. Decompose Unicode and drop combining characters (accent removal).
    3. Lowercase, replace non-alphanumeric with spaces.
    4. Remove tokens that are in ``_FUZZY_STRIP``.
    5. Return remaining tokens joined by space.
    """
    s = normalize_team_name(str(name))
    # Strip accents via NFKD decomposition
    nfkd = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase; punctuation → space
    s = re.sub(r"[^\w\s]", " ", s.lower())
    # Drop non-distinctive tokens
    tokens = [t for t in s.split() if t not in _FUZZY_STRIP]
    return " ".join(tokens).strip()
