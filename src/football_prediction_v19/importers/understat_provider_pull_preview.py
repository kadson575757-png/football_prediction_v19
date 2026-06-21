# -*- coding: utf-8 -*-
"""Controlled Understat provider pull preview."""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

UNDERSTAT_PROVIDER_PULL_PREVIEW_READY = "UNDERSTAT_PROVIDER_PULL_PREVIEW_READY"
UNDERSTAT_PROVIDER_PULL_PREVIEW_PARTIAL_READY = "UNDERSTAT_PROVIDER_PULL_PREVIEW_PARTIAL_READY"
UNDERSTAT_PROVIDER_PULL_BLOCKED_NETWORK_DISABLED = "UNDERSTAT_PROVIDER_PULL_BLOCKED_NETWORK_DISABLED"
UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT = "UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT"
UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH = "UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH"
UNDERSTAT_PROVIDER_PULL_BLOCKED_PARSE_ERROR = "UNDERSTAT_PROVIDER_PULL_BLOCKED_PARSE_ERROR"
UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS = "UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS"
UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING = "UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING"
UNDERSTAT_PROVIDER_PULL_NETWORK_ENABLED_EXPLICITLY = "UNDERSTAT_PROVIDER_PULL_NETWORK_ENABLED_EXPLICITLY"
UNDERSTAT_PROVIDER_PULL_NETWORK_DISABLED_BY_DEFAULT = "UNDERSTAT_PROVIDER_PULL_NETWORK_DISABLED_BY_DEFAULT"
UNDERSTAT_PROVIDER_PULL_NO_MODEL_INTEGRATION_BY_DESIGN = "UNDERSTAT_PROVIDER_PULL_NO_MODEL_INTEGRATION_BY_DESIGN"
UNDERSTAT_PROVIDER_PULL_NO_BETTING_INTEGRATION_BY_DESIGN = "UNDERSTAT_PROVIDER_PULL_NO_BETTING_INTEGRATION_BY_DESIGN"

PROVIDER = "understat"
NORMALIZED_COLUMNS = [
    "source_id", "provider", "provider_match_id", "league", "season", "match_date",
    "home_team", "away_team", "home_goals", "away_goals", "home_xg", "away_xg",
    "home_xga", "away_xga", "venue", "neutral_venue", "data_quality_status",
    "source_snapshot_path", "normalization_warning",
]
MANIFEST_COLUMNS = [
    "provider_pull_id", "provider", "source_id", "league", "season", "allow_network",
    "network_calls_enabled", "raw_snapshot_path", "normalized_output_path", "rows_raw",
    "rows_normalized", "rows_with_missing_required_values", "rows_with_missing_optional_values",
    "provider_pull_status", "recommendation", "notes",
]
REQUIRED_NORMALIZED = ["source_id", "provider_match_id", "league", "season", "match_date", "home_team", "away_team"]
OPTIONAL_NORMALIZED = ["home_xg", "away_xg", "home_xga", "away_xga", "venue", "neutral_venue"]
PROTECTED_PATH_TOKENS = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class UnderstatProviderPullConfig:
    league: str
    season: str
    input_path: str | Path | None = None
    output_dir: str | Path = "outputs/provider_pull_preview/understat"
    allow_network: bool = False
    write_preview: bool = True
    base_dir: str | Path = "."


@dataclass(frozen=True)
class UnderstatProviderPullResult:
    provider_pull_id: str
    provider: str
    source_id: str
    league: str
    season: str
    allow_network: bool
    network_calls_enabled: bool
    raw_snapshot_path: str
    normalized_output_path: str
    manifest_path: str
    rows_raw: int
    rows_normalized: int
    rows_with_missing_required_values: int
    rows_with_missing_optional_values: int
    provider_pull_status: str
    recommendation: str
    notes: str


class LocalUnderstatSnapshotReader:
    def read(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")


class UnderstatRawSnapshotWriter:
    def __init__(self, raw_dir: Path) -> None:
        self.raw_dir = raw_dir

    def write(self, payload: str, *, league: str, season: str) -> Path:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        path = self.raw_dir / f"understat_{_slug(league)}_{_slug(season)}_raw_snapshot.json"
        path.write_text(payload, encoding="utf-8")
        return path


class UnderstatPreviewNormalizer:
    def normalize(self, payload: str, *, league: str, season: str, source_snapshot_path: str = "") -> pd.DataFrame:
        rows = [_normalize_match(row, league=league, season=season, source_snapshot_path=source_snapshot_path) for row in _extract_matches(payload)]
        return pd.DataFrame(rows, columns=NORMALIZED_COLUMNS)


class UnderstatProviderPuller:
    def __init__(self, config: UnderstatProviderPullConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[UnderstatProviderPullResult, pd.DataFrame]:
        output_dir = _safe_provider_output_dir(self.config.output_dir, self.base)
        if output_dir is None:
            return self._blocked(UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        input_path = _resolve_input_path(self.config.input_path, self.base)
        if self.config.input_path is not None and (input_path is None or _unsafe_path(input_path)):
            return self._blocked(UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        if input_path is None and not self.config.allow_network:
            return self._blocked(UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        try:
            if input_path is not None:
                payload = LocalUnderstatSnapshotReader().read(input_path)
                network_enabled = False
                source_id = "understat_local_snapshot"
                raw_snapshot_path = str(UnderstatRawSnapshotWriter(output_dir / "raw").write(payload, league=self.config.league, season=self.config.season).resolve()) if self.config.write_preview else str(input_path.resolve())
            else:
                payload = self._fetch_remote()
                network_enabled = True
                source_id = "understat_network_pull"
                raw_snapshot_path = str(UnderstatRawSnapshotWriter(output_dir / "raw").write(payload, league=self.config.league, season=self.config.season).resolve())
            normalized = UnderstatPreviewNormalizer().normalize(payload, league=self.config.league, season=self.config.season, source_snapshot_path=raw_snapshot_path)
        except Exception as exc:
            return self._blocked(UNDERSTAT_PROVIDER_PULL_BLOCKED_PARSE_ERROR, notes=str(exc)), pd.DataFrame(columns=NORMALIZED_COLUMNS)

        missing_required = _missing_rows(normalized, REQUIRED_NORMALIZED)
        missing_optional = _missing_rows(normalized, OPTIONAL_NORMALIZED)
        if normalized.empty or missing_required == len(normalized):
            status = UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS
        elif missing_required > 0:
            status = UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS
        elif missing_optional > 0:
            status = UNDERSTAT_PROVIDER_PULL_PREVIEW_PARTIAL_READY
        else:
            status = UNDERSTAT_PROVIDER_PULL_PREVIEW_READY

        normalized_path = ""
        if self.config.write_preview and status in {UNDERSTAT_PROVIDER_PULL_PREVIEW_READY, UNDERSTAT_PROVIDER_PULL_PREVIEW_PARTIAL_READY}:
            normalized_dir = output_dir / "normalized"
            normalized_dir.mkdir(parents=True, exist_ok=True)
            normalized_file = normalized_dir / f"understat_{_slug(self.config.league)}_{_slug(self.config.season)}_normalized_preview.csv"
            normalized.to_csv(normalized_file, index=False)
            normalized_path = str(normalized_file.resolve())

        result = UnderstatProviderPullResult(
            provider_pull_id=f"understat_{_slug(self.config.league)}_{_slug(self.config.season)}",
            provider=PROVIDER,
            source_id=source_id,
            league=self.config.league,
            season=str(self.config.season),
            allow_network=bool(self.config.allow_network),
            network_calls_enabled=network_enabled,
            raw_snapshot_path=raw_snapshot_path,
            normalized_output_path=normalized_path,
            manifest_path="",
            rows_raw=len(normalized),
            rows_normalized=len(normalized),
            rows_with_missing_required_values=missing_required,
            rows_with_missing_optional_values=missing_optional,
            provider_pull_status=status,
            recommendation=status,
            notes=_notes(network_enabled, missing_optional),
        )
        if self.config.write_preview:
            manifest = self._write_manifest(output_dir, result)
            result = UnderstatProviderPullResult(**{**result.__dict__, "manifest_path": str(manifest.resolve())})
        return result, normalized

    def _fetch_remote(self) -> str:
        if not self.config.allow_network:
            raise RuntimeError(UNDERSTAT_PROVIDER_PULL_BLOCKED_NETWORK_DISABLED)
        url = f"https://understat.com/league/{self.config.league}/{self.config.season}"
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - explicitly gated preview fetch
            return response.read().decode("utf-8")

    def _write_manifest(self, output_dir: Path, result: UnderstatProviderPullResult) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "understat_provider_pull_manifest.csv"
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(path, index=False)
        return path

    def _blocked(self, status: str, notes: str = "") -> UnderstatProviderPullResult:
        return UnderstatProviderPullResult(
            provider_pull_id=f"understat_{_slug(self.config.league)}_{_slug(self.config.season)}",
            provider=PROVIDER,
            source_id="",
            league=self.config.league,
            season=str(self.config.season),
            allow_network=bool(self.config.allow_network),
            network_calls_enabled=False,
            raw_snapshot_path="",
            normalized_output_path="",
            manifest_path="",
            rows_raw=0,
            rows_normalized=0,
            rows_with_missing_required_values=0,
            rows_with_missing_optional_values=0,
            provider_pull_status=status,
            recommendation=status,
            notes=notes or f"{UNDERSTAT_PROVIDER_PULL_NETWORK_DISABLED_BY_DEFAULT}; {UNDERSTAT_PROVIDER_PULL_NO_MODEL_INTEGRATION_BY_DESIGN}; {UNDERSTAT_PROVIDER_PULL_NO_BETTING_INTEGRATION_BY_DESIGN}",
        )


def _extract_matches(payload: str) -> list[dict[str, Any]]:
    text = payload.strip()
    if not text:
        raise ValueError("empty Understat payload")
    if text.startswith("<"):
        match = re.search(r"understat_fixture_json\s*=\s*(?P<data>\[.*?\])\s*</script>", text, flags=re.DOTALL)
        if not match:
            raise ValueError("could not find Understat match payload in HTML")
        data: Any = json.loads(match.group("data"))
    else:
        data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("matches") or data.get("datesData") or data.get("fixtures") or []
    if not isinstance(data, list):
        raise ValueError("Understat payload must contain a list of matches")
    return [row for row in data if isinstance(row, dict)]


def _normalize_match(row: dict[str, Any], *, league: str, season: str, source_snapshot_path: str) -> dict[str, Any]:
    home = row.get("h") or row.get("home") or {}
    away = row.get("a") or row.get("away") or {}
    goals = row.get("goals") or {}
    xg = row.get("xG") or row.get("xg") or {}
    home_xg = _first(row, ["home_xg", "home_xG", "xG_home", "hxg"], xg.get("h"))
    away_xg = _first(row, ["away_xg", "away_xG", "xG_away", "axg"], xg.get("a"))
    values = {
        "source_id": "understat_provider_pull_preview",
        "provider": PROVIDER,
        "provider_match_id": str(row.get("id") or row.get("provider_match_id") or ""),
        "league": league,
        "season": str(season),
        "match_date": str(row.get("datetime") or row.get("date") or row.get("Date") or "")[:10],
        "home_team": _team_name(home) or row.get("home_team") or row.get("homeTeam") or "",
        "away_team": _team_name(away) or row.get("away_team") or row.get("awayTeam") or "",
        "home_goals": _empty_if_none(_first(row, ["home_goals", "homeGoals", "FTHG"], goals.get("h"))),
        "away_goals": _empty_if_none(_first(row, ["away_goals", "awayGoals", "FTAG"], goals.get("a"))),
        "home_xg": _empty_if_none(home_xg),
        "away_xg": _empty_if_none(away_xg),
        "home_xga": _empty_if_none(away_xg),
        "away_xga": _empty_if_none(home_xg),
        "venue": _empty_if_none(row.get("venue")),
        "neutral_venue": _empty_if_none(row.get("neutral_venue")),
        "data_quality_status": "UNDERSTAT_PROVIDER_PULL_PREVIEW_ROW",
        "source_snapshot_path": source_snapshot_path,
        "normalization_warning": "",
    }
    missing_optional = [column for column in OPTIONAL_NORMALIZED if str(values[column]).strip() == ""]
    if missing_optional:
        values["normalization_warning"] = UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING + ":" + " | ".join(missing_optional)
    return values


def _first(row: dict[str, Any], keys: list[str], fallback: Any = None) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return fallback


def _team_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("title") or value.get("name") or "").strip()
    return str(value or "").strip()


def _missing_rows(frame: pd.DataFrame, columns: list[str]) -> int:
    if frame.empty:
        return 0
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        mask = mask | frame[column].isna() | frame[column].astype(str).str.strip().eq("")
    return int(mask.sum())


def _notes(network_enabled: bool, missing_optional: int) -> str:
    notes = [UNDERSTAT_PROVIDER_PULL_NETWORK_ENABLED_EXPLICITLY if network_enabled else UNDERSTAT_PROVIDER_PULL_NETWORK_DISABLED_BY_DEFAULT]
    if missing_optional:
        notes.append(UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING)
    notes.extend([UNDERSTAT_PROVIDER_PULL_NO_MODEL_INTEGRATION_BY_DESIGN, UNDERSTAT_PROVIDER_PULL_NO_BETTING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)


def _safe_provider_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "provider_pull_preview" / "understat").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _resolve_input_path(input_path: str | Path | None, base_dir: Path) -> Path | None:
    if input_path is None:
        return None
    path = Path(input_path)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _unsafe_path(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    if text.startswith(("http://", "https://")):
        return True
    return any(token in text for token in PROTECTED_PATH_TOKENS)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _empty_if_none(value: Any) -> Any:
    return "" if value is None else value
