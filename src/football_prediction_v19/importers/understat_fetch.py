# -*- coding: utf-8 -*-
"""Controlled Understat league/season fetch pilot.

Phase 13.6 diagnostic/foundation only. Runtime fetching happens only when the
user explicitly calls the CLI with a league/season or URL. Tests use local HTML
fixtures and never call the network.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd

UNDERSTAT_FETCH_READY = "UNDERSTAT_FETCH_READY"
UNDERSTAT_FETCH_BLOCKED_NO_INPUT = "UNDERSTAT_FETCH_BLOCKED_NO_INPUT"
UNDERSTAT_FETCH_BLOCKED_UNSUPPORTED_LEAGUE = "UNDERSTAT_FETCH_BLOCKED_UNSUPPORTED_LEAGUE"
UNDERSTAT_FETCH_BLOCKED_FETCH_FAILED = "UNDERSTAT_FETCH_BLOCKED_FETCH_FAILED"
UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED = "UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED"
UNDERSTAT_FETCH_BLOCKED_NO_MATCHES_FOUND = "UNDERSTAT_FETCH_BLOCKED_NO_MATCHES_FOUND"
UNDERSTAT_FETCH_BLOCKED_INVALID_XG_VALUES = "UNDERSTAT_FETCH_BLOCKED_INVALID_XG_VALUES"
UNDERSTAT_FETCH_BLOCKED_OUTPUT_EXISTS = "UNDERSTAT_FETCH_BLOCKED_OUTPUT_EXISTS"

OUTPUT_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_xg",
    "away_xg",
    "xg_source_name",
    "xg_source_url",
    "xg_import_type",
]

LEAGUE_ALIASES = {
    "bundesliga": "Bundesliga",
    "d1": "Bundesliga",
    "germany": "Bundesliga",
    "germanybundesliga": "Bundesliga",
    "epl": "EPL",
    "premierleague": "EPL",
    "england": "EPL",
    "laliga": "La_liga",
    "spain": "La_liga",
    "seriea": "Serie_A",
    "italy": "Serie_A",
    "ligue1": "Ligue_1",
    "france": "Ligue_1",
}


@dataclass(frozen=True)
class UnderstatFetchResult:
    league: str
    season: str
    source_url: str
    raw_output_path: str
    output_path: str
    matches_found: int
    rows_normalized: int
    fetch_label: str
    validation_errors: list[str]
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve(path: str | Path) -> Path:
    out = Path(path)
    if not out.is_absolute():
        out = _repo_root() / out
    return out


def _norm_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def normalize_understat_league_name(league: str | None) -> str | None:
    if league is None or str(league).strip() == "":
        return None
    return LEAGUE_ALIASES.get(_norm_key(league))


def build_understat_league_url(league: str, season: str | int) -> str:
    normalized = normalize_understat_league_name(league)
    if not normalized:
        raise ValueError("UNSUPPORTED_UNDERSTAT_LEAGUE")
    return f"https://understat.com/league/{normalized}/{season}"


def _safe_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    base = "_".join(parts[-3:]) if parts else "understat_fetch"
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base)
    if "understat" not in safe.lower():
        safe = f"understat_{safe}"
    return f"{safe}.html"


def fetch_understat_html(url: str, raw_output_dir: str | Path = "data/trusted_xg_sources/raw", overwrite: bool = False) -> Path:
    output_root = _resolve(raw_output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / _safe_name_from_url(url)).resolve()
    if output_root.resolve() not in output.parents:
        raise ValueError("Understat raw HTML must stay under raw_output_dir")
    if output.exists() and not overwrite:
        raise FileExistsError(str(output))
    request = Request(url, headers={"User-Agent": "football_prediction_v19 understat-fetch/13.6"})
    with urlopen(request, timeout=30) as response:
        html = response.read()
    output.write_bytes(html)
    return output


def _decode_understat_json_literal(raw: str) -> str:
    decoded = raw.encode("utf-8").decode("unicode_escape")
    return decoded.replace("\\/", "/")


def parse_understat_matches_from_html(html: str, source_url: str | None = None) -> list[dict[str, Any]]:
    patterns = [
        r"datesData\s*=\s*JSON\.parse\('(?P<data>.*?)'\)",
        r"matchesData\s*=\s*JSON\.parse\('(?P<data>.*?)'\)",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(_decode_understat_json_literal(match.group("data")))
            except Exception as exc:
                raise ValueError(f"UNDERSTAT_EMBEDDED_JSON_PARSE_FAILED: {exc}") from exc
            if isinstance(parsed, dict):
                parsed = list(parsed.values())
            if not isinstance(parsed, list):
                raise ValueError("UNDERSTAT_EMBEDDED_JSON_NOT_LIST")
            return [row for row in parsed if isinstance(row, dict)]
    raise ValueError("UNDERSTAT_MATCH_DATA_NOT_FOUND")


def _team_name(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("title", "name", "short_title"):
            if key in value and str(value[key]).strip():
                return " ".join(str(value[key]).strip().split())
    return " ".join(str(value or "").strip().split())


def _get_xg(match: dict[str, Any], side: str) -> Any:
    xg = match.get("xG")
    if isinstance(xg, dict):
        return xg.get(side)
    return match.get(f"{side}_xg") or match.get(f"{side}xG") or match.get(f"{side}_xG")


def normalize_understat_matches_to_trusted_xg(matches: list[dict[str, Any]], source_url: str | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for match in matches:
        home = _team_name(match.get("h") or match.get("home") or match.get("home_team"))
        away = _team_name(match.get("a") or match.get("away") or match.get("away_team"))
        date_value = match.get("datetime") or match.get("date")
        rows.append({
            "date": date_value,
            "home_team": home,
            "away_team": away,
            "home_xg": _get_xg(match, "h"),
            "away_xg": _get_xg(match, "a"),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    out["date"] = pd.to_datetime(out["date"], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")
    identity_missing = out[["date", "home_team", "away_team"]].isna().any(axis=1) | out[["home_team", "away_team"]].astype(str).apply(lambda col: col.str.strip().eq("")).any(axis=1)
    if identity_missing.any():
        raise ValueError("UNDERSTAT_MATCH_IDENTITY_MISSING")
    raw = out[["home_xg", "away_xg"]]
    missing = raw.isna() | raw.astype(str).apply(lambda col: col.str.strip().eq(""))
    if missing.any().any():
        raise ValueError("MISSING_XG_VALUES")
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        raise ValueError("NON_NUMERIC_XG_VALUES")
    if (numeric < 0).any().any():
        raise ValueError("NEGATIVE_XG_VALUES")
    out["home_xg"] = numeric["home_xg"]
    out["away_xg"] = numeric["away_xg"]
    out["xg_source_name"] = "understat_fetch"
    out["xg_source_url"] = source_url or ""
    out["xg_import_type"] = "UNDERSTAT_FETCH"
    return out[OUTPUT_COLUMNS]


def write_understat_fetch_trusted_xg_csv(
    df: pd.DataFrame,
    output_name: str,
    output_dir: str | Path = "data/trusted_xg_sources",
    overwrite: bool = False,
) -> Path:
    output_root = _resolve(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(output_name).name
    if not safe_name.lower().endswith(".csv"):
        safe_name = f"{safe_name}.csv"
    if "understat" not in safe_name.lower():
        safe_name = f"understat_{safe_name}"
    output = (output_root / safe_name).resolve()
    if output_root.resolve() not in output.parents:
        raise ValueError("Understat normalized CSV must stay under output_dir")
    if output.exists() and not overwrite:
        raise FileExistsError(str(output))
    df.to_csv(output, index=False)
    return output


def _blocked(
    label: str,
    errors: list[str],
    *,
    league: str = "",
    season: str = "",
    source_url: str = "",
    raw_output_path: str = "",
    matches_found: int = 0,
) -> UnderstatFetchResult:
    return UnderstatFetchResult(
        league=league,
        season=season,
        source_url=source_url,
        raw_output_path=raw_output_path,
        output_path="",
        matches_found=int(matches_found),
        rows_normalized=0,
        fetch_label=label,
        validation_errors=errors,
        warning_notes=[],
    )


def _label_for_normalize_error(exc: Exception) -> str:
    text = str(exc)
    if any(token in text for token in ("MISSING_XG_VALUES", "NON_NUMERIC_XG_VALUES", "NEGATIVE_XG_VALUES")):
        return UNDERSTAT_FETCH_BLOCKED_INVALID_XG_VALUES
    return UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED


def fetch_understat_league_season(
    league: str | None = None,
    season: str | int | None = None,
    url: str | None = None,
    output_name: str | None = None,
    output_dir: str | Path = "data/trusted_xg_sources",
    raw_output_dir: str | Path = "data/trusted_xg_sources/raw",
    overwrite: bool = False,
    no_fetch: bool = False,
) -> UnderstatFetchResult:
    if not url and not (league and season):
        return _blocked(UNDERSTAT_FETCH_BLOCKED_NO_INPUT, ["URL_OR_LEAGUE_AND_SEASON_REQUIRED"], league=str(league or ""), season=str(season or ""))
    normalized_league = normalize_understat_league_name(league) if league else ""
    if not url and not normalized_league:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_UNSUPPORTED_LEAGUE, ["UNSUPPORTED_UNDERSTAT_LEAGUE"], league=str(league or ""), season=str(season or ""))
    source_url = url or build_understat_league_url(str(league), str(season))
    if no_fetch:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_FETCH_FAILED, ["NO_FETCH_REQUESTED"], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url)
    try:
        raw_path = fetch_understat_html(source_url, raw_output_dir=raw_output_dir, overwrite=overwrite)
        html = raw_path.read_text(encoding="utf-8", errors="replace")
    except FileExistsError as exc:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_OUTPUT_EXISTS, [str(exc)], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url)
    except Exception as exc:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_FETCH_FAILED, [str(exc)], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url)
    try:
        matches = parse_understat_matches_from_html(html, source_url=source_url)
    except Exception as exc:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED, [str(exc)], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url, raw_output_path=str(raw_path))
    if not matches:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_NO_MATCHES_FOUND, ["NO_MATCHES_FOUND"], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url, raw_output_path=str(raw_path))
    try:
        normalized = normalize_understat_matches_to_trusted_xg(matches, source_url=source_url)
    except Exception as exc:
        return _blocked(_label_for_normalize_error(exc), [str(exc)], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url, raw_output_path=str(raw_path), matches_found=len(matches))
    if normalized.empty:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_NO_MATCHES_FOUND, ["NO_MATCHES_FOUND"], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url, raw_output_path=str(raw_path))
    name = output_name or f"understat_xg_{(normalized_league or 'custom').lower()}_{season or 'url'}.csv"
    try:
        output_path = write_understat_fetch_trusted_xg_csv(normalized, name, output_dir=output_dir, overwrite=overwrite)
    except FileExistsError as exc:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_OUTPUT_EXISTS, [str(exc)], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url, raw_output_path=str(raw_path), matches_found=len(matches))
    except Exception as exc:
        return _blocked(UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED, [str(exc)], league=normalized_league or str(league or ""), season=str(season or ""), source_url=source_url, raw_output_path=str(raw_path), matches_found=len(matches))
    return UnderstatFetchResult(
        league=normalized_league or str(league or ""),
        season=str(season or ""),
        source_url=source_url,
        raw_output_path=str(raw_path),
        output_path=str(output_path),
        matches_found=len(matches),
        rows_normalized=len(normalized),
        fetch_label=UNDERSTAT_FETCH_READY,
        validation_errors=[],
        warning_notes=["Fetched Understat xG is not used by the model until intake, acceptance, and future enrichment are approved."],
    )
