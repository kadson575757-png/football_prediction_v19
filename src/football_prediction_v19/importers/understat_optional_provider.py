# -*- coding: utf-8 -*-
"""Optional soccerdata Understat provider bootstrap helpers.

Phase 13.8 diagnostic/foundation only. soccerdata remains optional and is never
imported at module import time.
"""
from __future__ import annotations

import importlib
import importlib.metadata
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.importers.understat_trusted_xg import OUTPUT_COLUMNS

UNDERSTAT_OPTIONAL_PROVIDER_AVAILABLE = "UNDERSTAT_OPTIONAL_PROVIDER_AVAILABLE"
UNDERSTAT_OPTIONAL_PROVIDER_UNAVAILABLE = "UNDERSTAT_OPTIONAL_PROVIDER_UNAVAILABLE"
UNDERSTAT_OPTIONAL_PROVIDER_IMPORT_ERROR = "UNDERSTAT_OPTIONAL_PROVIDER_IMPORT_ERROR"
UNDERSTAT_OPTIONAL_PROVIDER_UNSUPPORTED_VERSION = "UNDERSTAT_OPTIONAL_PROVIDER_UNSUPPORTED_VERSION"


@dataclass(frozen=True)
class UnderstatOptionalProviderStatus:
    provider_name: str
    installed: bool
    import_error: str
    version: str
    available_classes: list[str]
    provider_label: str
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {"".join(ch for ch in str(col).lower() if ch.isalnum()): str(col) for col in df.columns}
    for name in names:
        key = "".join(ch for ch in name.lower() if ch.isalnum())
        if key in by_norm:
            return by_norm[key]
    return None


def get_understat_optional_provider_install_command(python_executable: str | None = None) -> str:
    python = python_executable or sys.executable
    req = Path("requirements-understat-optional.txt")
    return f'"{python}" -m pip install -r {req}'


def get_understat_optional_provider_usage_notes() -> list[str]:
    return [
        "soccerdata is optional and is not required for normal model operation.",
        "No xG values are inferred or invented by the optional provider path.",
        "Model behavior remains unchanged until a future accepted enrichment integration is implemented.",
    ]


def check_understat_optional_provider() -> UnderstatOptionalProviderStatus:
    provider_name = "soccerdata"
    if sys.modules.get(provider_name) is None:
        spec = importlib.util.find_spec(provider_name) if provider_name not in sys.modules else None
    else:
        spec = True
    if spec is None:
        return UnderstatOptionalProviderStatus(
            provider_name=provider_name,
            installed=False,
            import_error="",
            version="",
            available_classes=[],
            provider_label=UNDERSTAT_OPTIONAL_PROVIDER_UNAVAILABLE,
            warning_notes=["Install explicitly with: " + get_understat_optional_provider_install_command()],
        )
    try:
        module = importlib.import_module(provider_name)
    except Exception as exc:
        return UnderstatOptionalProviderStatus(
            provider_name=provider_name,
            installed=True,
            import_error=str(exc),
            version="",
            available_classes=[],
            provider_label=UNDERSTAT_OPTIONAL_PROVIDER_IMPORT_ERROR,
            warning_notes=get_understat_optional_provider_usage_notes(),
        )
    try:
        version = importlib.metadata.version(provider_name)
    except Exception:
        version = getattr(module, "__version__", "")
    available_classes = [name for name in ("Understat",) if hasattr(module, name)]
    label = UNDERSTAT_OPTIONAL_PROVIDER_AVAILABLE if "Understat" in available_classes else UNDERSTAT_OPTIONAL_PROVIDER_UNSUPPORTED_VERSION
    return UnderstatOptionalProviderStatus(
        provider_name=provider_name,
        installed=True,
        import_error="",
        version=str(version or ""),
        available_classes=available_classes,
        provider_label=label,
        warning_notes=get_understat_optional_provider_usage_notes(),
    )


def load_soccerdata_understat_provider() -> Any:
    status = check_understat_optional_provider()
    if status.provider_label != UNDERSTAT_OPTIONAL_PROVIDER_AVAILABLE:
        raise ImportError(status.provider_label)
    module = importlib.import_module("soccerdata")
    return getattr(module, "Understat")


def normalize_soccerdata_understat_output(
    df: pd.DataFrame,
    league: str | None = None,
    season: str | int | None = None,
) -> pd.DataFrame:
    date = _find_col(df, "date", "game_date", "datetime")
    home = _find_col(df, "home_team", "home")
    away = _find_col(df, "away_team", "away")
    hxg = _find_col(df, "home_xg", "home_xG", "hxg", "h_xg")
    axg = _find_col(df, "away_xg", "away_xG", "axg", "a_xg")
    if not all([date, home, away, hxg, axg]):
        raise ValueError("OPTIONAL_PROVIDER_SCHEMA_UNSUPPORTED")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[str(date)], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d"),
        "home_team": df[str(home)].astype(str).str.strip(),
        "away_team": df[str(away)].astype(str).str.strip(),
        "home_xg": df[str(hxg)],
        "away_xg": df[str(axg)],
    })
    raw = out[["home_xg", "away_xg"]]
    missing = raw.isna() | raw.astype(str).apply(lambda col: col.str.strip().eq(""))
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    if missing.any().any():
        raise ValueError("MISSING_XG_VALUES")
    if numeric.isna().any().any():
        raise ValueError("NON_NUMERIC_XG_VALUES")
    if (numeric < 0).any().any():
        raise ValueError("NEGATIVE_XG_VALUES")
    out["home_xg"] = numeric["home_xg"]
    out["away_xg"] = numeric["away_xg"]
    out["xg_source_name"] = "soccerdata_understat"
    out["xg_source_url"] = ""
    out["xg_import_type"] = "OPTIONAL_PROVIDER"
    return out[OUTPUT_COLUMNS]
