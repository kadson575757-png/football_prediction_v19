# -*- coding: utf-8 -*-
"""FBref provider pull preview for local/offline team match context."""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

import pandas as pd

FBREF_PROVIDER_PULL_PREVIEW_READY = "FBREF_PROVIDER_PULL_PREVIEW_READY"
FBREF_PROVIDER_PULL_OFFLINE_READY = "FBREF_PROVIDER_PULL_OFFLINE_READY"
FBREF_PROVIDER_PULL_BLOCKED_NETWORK_DISABLED = "FBREF_PROVIDER_PULL_BLOCKED_NETWORK_DISABLED"
FBREF_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT = "FBREF_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT"
FBREF_PROVIDER_PULL_BLOCKED_UNSAFE_PATH = "FBREF_PROVIDER_PULL_BLOCKED_UNSAFE_PATH"
FBREF_PROVIDER_PULL_BLOCKED_FETCH_ERROR = "FBREF_PROVIDER_PULL_BLOCKED_FETCH_ERROR"
FBREF_PROVIDER_PULL_BLOCKED_PARSE_ERROR = "FBREF_PROVIDER_PULL_BLOCKED_PARSE_ERROR"
FBREF_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS = "FBREF_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS"
FBREF_PROVIDER_PULL_OPTIONAL_VALUES_MISSING = "FBREF_PROVIDER_PULL_OPTIONAL_VALUES_MISSING"
FBREF_PROVIDER_PULL_NETWORK_ENABLED_EXPLICITLY = "FBREF_PROVIDER_PULL_NETWORK_ENABLED_EXPLICITLY"
FBREF_PROVIDER_PULL_NETWORK_DISABLED_BY_DEFAULT = "FBREF_PROVIDER_PULL_NETWORK_DISABLED_BY_DEFAULT"
FBREF_PROVIDER_PULL_NO_MODEL_INTEGRATION_BY_DESIGN = "FBREF_PROVIDER_PULL_NO_MODEL_INTEGRATION_BY_DESIGN"
FBREF_PROVIDER_PULL_NO_BETTING_INTEGRATION_BY_DESIGN = "FBREF_PROVIDER_PULL_NO_BETTING_INTEGRATION_BY_DESIGN"

NORMALIZED_COLUMNS = [
    "source_id", "provider", "provider_match_id", "cross_provider_match_key",
    "understat_provider_match_id", "competition", "season", "match_date",
    "home_team", "away_team", "home_goals", "away_goals", "home_possession",
    "away_possession", "home_shots", "away_shots", "home_shots_on_target",
    "away_shots_on_target", "home_pass_completion_pct", "away_pass_completion_pct",
    "home_progressive_passes", "away_progressive_passes", "home_progressive_carries",
    "away_progressive_carries", "home_touches_att_pen_area", "away_touches_att_pen_area",
    "home_tackles", "away_tackles", "home_interceptions", "away_interceptions",
    "home_blocks", "away_blocks", "home_clearances", "away_clearances",
    "data_quality_status", "source_snapshot_path", "normalization_warning",
]
REQUIRED_COLUMNS = ["source_id", "provider", "provider_match_id", "competition", "season", "match_date", "home_team", "away_team"]
OPTIONAL_COLUMNS = [c for c in NORMALIZED_COLUMNS if c not in REQUIRED_COLUMNS and c not in {"normalization_warning", "source_snapshot_path", "data_quality_status"}]
MANIFEST_COLUMNS = [
    "fbref_pull_run_id", "provider", "source_id", "competition", "season",
    "allow_network", "network_calls_enabled", "local_input_path", "raw_output_path",
    "normalized_output_path", "rows_raw", "rows_normalized",
    "rows_with_missing_required_values", "rows_with_missing_optional_values",
    "fbref_provider_pull_status", "recommendation", "notes",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class FBrefProviderPullConfig:
    competition: str = "Bundesliga"
    season: str = "2024"
    local_input: str | Path | None = None
    output_dir: str | Path = "outputs/provider_pull_preview/fbref"
    allow_network: bool = False
    write_preview: bool = True
    base_dir: str | Path = "."
    fetcher: Callable[[str, str], str] | None = None


@dataclass(frozen=True)
class FBrefProviderPullResult:
    fbref_pull_run_id: str
    provider: str
    source_id: str
    competition: str
    season: str
    allow_network: bool
    network_calls_enabled: bool
    local_input_path: str
    raw_output_path: str
    normalized_output_path: str
    manifest_path: str
    rows_raw: int
    rows_normalized: int
    rows_with_missing_required_values: int
    rows_with_missing_optional_values: int
    fbref_provider_pull_status: str
    recommendation: str
    notes: str


class FBrefFetcher:
    def fetch(self, competition: str, season: str) -> str:
        url = f"https://fbref.com/en/comps/{competition}/{season}"
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - explicitly gated preview fetch
            return response.read().decode("utf-8")


class FBrefProviderPullPreviewRunner:
    def __init__(self, config: FBrefProviderPullConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[FBrefProviderPullResult, pd.DataFrame]:
        out = _safe_output_dir(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(FBREF_PROVIDER_PULL_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        local = _resolve_optional(self.config.local_input, self.base)
        if local is None and not self.config.allow_network:
            local = _default_fixture()
        if local is not None and _unsafe(local):
            return self._blocked(FBREF_PROVIDER_PULL_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        if local is None and not self.config.allow_network:
            return self._blocked(FBREF_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        try:
            if local is not None:
                if not local.exists():
                    return self._blocked(FBREF_PROVIDER_PULL_BLOCKED_MISSING_LOCAL_INPUT), pd.DataFrame(columns=NORMALIZED_COLUMNS)
                payload = local.read_text(encoding="utf-8")
                network = False
                source_id = "fbref_local_fixture"
                local_text = str(local.resolve())
            else:
                try:
                    payload = self.config.fetcher(self.config.competition, self.config.season) if self.config.fetcher else FBrefFetcher().fetch(self.config.competition, self.config.season)
                except Exception as exc:
                    return self._blocked(FBREF_PROVIDER_PULL_BLOCKED_FETCH_ERROR, notes=str(exc)), pd.DataFrame(columns=NORMALIZED_COLUMNS)
                network = True
                source_id = "fbref_live_fetch"
                local_text = ""
            rows = _extract_rows(payload)
            raw_path = self._write_raw(out, payload) if self.config.write_preview else ""
            frame = pd.DataFrame([_normalize_row(r, self.config.competition, str(self.config.season), raw_path) for r in rows], columns=NORMALIZED_COLUMNS)
        except Exception as exc:
            return self._blocked(FBREF_PROVIDER_PULL_BLOCKED_PARSE_ERROR, notes=str(exc)), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        missing_required = _missing_rows(frame, REQUIRED_COLUMNS)
        missing_optional = _missing_rows(frame, OPTIONAL_COLUMNS)
        status = FBREF_PROVIDER_PULL_BLOCKED_MISSING_REQUIRED_COLUMNS if frame.empty or missing_required else FBREF_PROVIDER_PULL_PREVIEW_READY
        normalized_path = ""
        if self.config.write_preview and status == FBREF_PROVIDER_PULL_PREVIEW_READY:
            normalized_dir = out / "normalized"
            normalized_dir.mkdir(parents=True, exist_ok=True)
            normalized = normalized_dir / "fbref_provider_pull_normalized.csv"
            frame.to_csv(normalized, index=False)
            normalized_path = str(normalized.resolve())
        result = FBrefProviderPullResult(
            fbref_pull_run_id="fbref_provider_pull_preview",
            provider="fbref",
            source_id=source_id,
            competition=self.config.competition,
            season=str(self.config.season),
            allow_network=bool(self.config.allow_network),
            network_calls_enabled=network,
            local_input_path=local_text,
            raw_output_path=raw_path,
            normalized_output_path=normalized_path,
            manifest_path="",
            rows_raw=len(frame),
            rows_normalized=len(frame),
            rows_with_missing_required_values=missing_required,
            rows_with_missing_optional_values=missing_optional,
            fbref_provider_pull_status=status,
            recommendation=FBREF_PROVIDER_PULL_PREVIEW_READY if status == FBREF_PROVIDER_PULL_PREVIEW_READY else status,
            notes=_notes(network, missing_optional),
        )
        if self.config.write_preview:
            manifest = out / "fbref_provider_pull_manifest.csv"
            out.mkdir(parents=True, exist_ok=True)
            pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest, index=False)
            result = FBrefProviderPullResult(**{**result.__dict__, "manifest_path": str(manifest.resolve())})
        return result, frame

    def _write_raw(self, out: Path, payload: str) -> str:
        raw_dir = out / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        path = raw_dir / "fbref_provider_pull_raw.json"
        path.write_text(payload, encoding="utf-8")
        return str(path.resolve())

    def _blocked(self, status: str, notes: str = "") -> FBrefProviderPullResult:
        return FBrefProviderPullResult("fbref_provider_pull_preview", "fbref", "", self.config.competition, str(self.config.season), bool(self.config.allow_network), False, str(self.config.local_input or ""), "", "", "", 0, 0, 0, 0, status, status, notes or _notes(False, 0))


def _extract_rows(payload: str) -> list[dict[str, Any]]:
    data = json.loads(payload)
    rows = data.get("matches", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("FBref payload must contain match rows")
    return [r for r in rows if isinstance(r, dict)]


def _normalize_row(row: dict[str, Any], competition: str, season: str, source_path: str) -> dict[str, Any]:
    values = {c: "" for c in NORMALIZED_COLUMNS}
    values.update({
        "source_id": "fbref_provider_pull_preview",
        "provider": "fbref",
        "provider_match_id": row.get("provider_match_id") or row.get("id") or "",
        "cross_provider_match_key": row.get("cross_provider_match_key", ""),
        "understat_provider_match_id": row.get("understat_provider_match_id", ""),
        "competition": row.get("competition", competition),
        "season": str(row.get("season", season)),
        "match_date": str(row.get("match_date") or row.get("date") or "")[:10],
        "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""),
        "data_quality_status": "FBREF_PROVIDER_PULL_PREVIEW_ROW",
        "source_snapshot_path": source_path,
    })
    for key in OPTIONAL_COLUMNS:
        if key in row:
            values[key] = row[key]
    missing = [c for c in OPTIONAL_COLUMNS if str(values.get(c, "")).strip() == ""]
    if missing:
        values["normalization_warning"] = FBREF_PROVIDER_PULL_OPTIONAL_VALUES_MISSING + ":" + " | ".join(missing)
    return values


def _default_fixture() -> Path | None:
    path = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "fbref" / "fbref_bundesliga_2024_fixture.json"
    return path if path.exists() else None


def _safe_output_dir(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "provider_pull_preview" / "fbref").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _resolve_optional(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _missing_rows(frame: pd.DataFrame, columns: list[str]) -> int:
    if frame.empty:
        return 0
    mask = pd.Series(False, index=frame.index)
    for c in columns:
        mask = mask | frame[c].isna() | frame[c].astype(str).str.strip().eq("")
    return int(mask.sum())


def _notes(network: bool, missing_optional: int) -> str:
    notes = [FBREF_PROVIDER_PULL_NETWORK_ENABLED_EXPLICITLY if network else FBREF_PROVIDER_PULL_NETWORK_DISABLED_BY_DEFAULT]
    if missing_optional:
        notes.append(FBREF_PROVIDER_PULL_OPTIONAL_VALUES_MISSING)
    notes.extend([FBREF_PROVIDER_PULL_NO_MODEL_INTEGRATION_BY_DESIGN, FBREF_PROVIDER_PULL_NO_BETTING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
