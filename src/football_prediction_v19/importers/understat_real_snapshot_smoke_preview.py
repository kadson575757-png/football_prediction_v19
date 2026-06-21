# -*- coding: utf-8 -*-
"""Controlled real Understat snapshot smoke preview."""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from football_prediction_v19.importers.understat_provider_pull_preview import (
    NORMALIZED_COLUMNS,
    OPTIONAL_NORMALIZED,
    REQUIRED_NORMALIZED,
    UnderstatPreviewNormalizer,
)

UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_NETWORK_DISABLED = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_NETWORK_DISABLED"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_LOCAL_INPUT = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_LOCAL_INPUT"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_UNSAFE_PATH = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_UNSAFE_PATH"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_FETCH_ERROR = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_FETCH_ERROR"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_PARSE_ERROR = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_PARSE_ERROR"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_REQUIRED_COLUMNS = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_REQUIRED_COLUMNS"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_OPTIONAL_VALUES_MISSING = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_OPTIONAL_VALUES_MISSING"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_NETWORK_ENABLED_EXPLICITLY = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_NETWORK_ENABLED_EXPLICITLY"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_NETWORK_DISABLED_BY_DEFAULT = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_NETWORK_DISABLED_BY_DEFAULT"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_NO_MODEL_INTEGRATION_BY_DESIGN = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_NO_MODEL_INTEGRATION_BY_DESIGN"
UNDERSTAT_REAL_SNAPSHOT_SMOKE_NO_BETTING_INTEGRATION_BY_DESIGN = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_NO_BETTING_INTEGRATION_BY_DESIGN"

MANIFEST_COLUMNS = [
    "real_snapshot_run_id", "provider", "source_id", "league", "season",
    "allow_network", "network_calls_enabled", "local_snapshot_input_path",
    "raw_snapshot_path", "normalized_output_path", "rows_raw", "rows_normalized",
    "rows_with_missing_required_values", "rows_with_missing_optional_values",
    "real_snapshot_status", "recommendation", "notes",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class UnderstatRealSnapshotSmokeConfig:
    league: str = "Bundesliga"
    season: str = "2024"
    local_snapshot: str | Path | None = None
    output_dir: str | Path = "outputs/provider_pull_preview/understat/real_snapshot"
    allow_network: bool = False
    write_preview: bool = True
    base_dir: str | Path = "."
    fetcher: Callable[[str, str], str] | None = None


@dataclass(frozen=True)
class UnderstatRealSnapshotSmokeResult:
    real_snapshot_run_id: str
    provider: str
    source_id: str
    league: str
    season: str
    allow_network: bool
    network_calls_enabled: bool
    local_snapshot_input_path: str
    raw_snapshot_path: str
    normalized_output_path: str
    manifest_path: str
    rows_raw: int
    rows_normalized: int
    rows_with_missing_required_values: int
    rows_with_missing_optional_values: int
    real_snapshot_status: str
    recommendation: str
    notes: str


class UnderstatLiveFetcher:
    def fetch(self, league: str, season: str) -> str:
        url = f"https://understat.com/league/{league}/{season}"
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - explicit opt-in smoke path
            return response.read().decode("utf-8")


class UnderstatRealSnapshotSmokeRunner:
    def __init__(self, config: UnderstatRealSnapshotSmokeConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[UnderstatRealSnapshotSmokeResult, pd.DataFrame]:
        out = _safe_output_dir(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        local = _resolve_optional(self.config.local_snapshot, self.base)
        if local is not None and _unsafe_path(local):
            return self._blocked(UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        if local is None and not self.config.allow_network:
            return self._blocked(UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        try:
            if local is not None:
                if not local.exists():
                    return self._blocked(UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_LOCAL_INPUT), pd.DataFrame(columns=NORMALIZED_COLUMNS)
                payload = local.read_text(encoding="utf-8")
                network = False
                source_id = "understat_real_snapshot_local"
                local_text = str(local.resolve())
            else:
                try:
                    payload = self.config.fetcher(self.config.league, self.config.season) if self.config.fetcher else UnderstatLiveFetcher().fetch(self.config.league, self.config.season)
                except Exception as exc:
                    return self._blocked(UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_FETCH_ERROR, notes=str(exc)), pd.DataFrame(columns=NORMALIZED_COLUMNS)
                network = True
                source_id = "understat_real_snapshot_live"
                local_text = ""
            raw_path = self._write_raw(out, payload) if self.config.write_preview else ""
            frame = UnderstatPreviewNormalizer().normalize(payload, league=self.config.league, season=str(self.config.season), source_snapshot_path=raw_path)
        except Exception as exc:
            return self._blocked(UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_PARSE_ERROR, notes=str(exc)), pd.DataFrame(columns=NORMALIZED_COLUMNS)
        missing_required = _missing_rows(frame, REQUIRED_NORMALIZED)
        missing_optional = _missing_rows(frame, OPTIONAL_NORMALIZED)
        if frame.empty or missing_required:
            status = UNDERSTAT_REAL_SNAPSHOT_SMOKE_BLOCKED_MISSING_REQUIRED_COLUMNS
        else:
            status = UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY
        normalized_path = ""
        manifest_path = ""
        if self.config.write_preview and status == UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY:
            normalized_dir = out / "normalized"
            normalized_dir.mkdir(parents=True, exist_ok=True)
            normalized_file = normalized_dir / "understat_real_snapshot_normalized.csv"
            frame.to_csv(normalized_file, index=False)
            normalized_path = str(normalized_file.resolve())
        result = UnderstatRealSnapshotSmokeResult(
            real_snapshot_run_id="understat_real_snapshot_smoke_preview",
            provider="understat",
            source_id=source_id,
            league=self.config.league,
            season=str(self.config.season),
            allow_network=bool(self.config.allow_network),
            network_calls_enabled=network,
            local_snapshot_input_path=local_text,
            raw_snapshot_path=raw_path,
            normalized_output_path=normalized_path,
            manifest_path="",
            rows_raw=len(frame),
            rows_normalized=len(frame),
            rows_with_missing_required_values=missing_required,
            rows_with_missing_optional_values=missing_optional,
            real_snapshot_status=status,
            recommendation=UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY if status in {UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY, UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY} else status,
            notes=_notes(network, missing_optional),
        )
        if self.config.write_preview:
            manifest = out / "understat_real_snapshot_manifest.csv"
            out.mkdir(parents=True, exist_ok=True)
            pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest, index=False)
            result = UnderstatRealSnapshotSmokeResult(**{**result.__dict__, "manifest_path": str(manifest.resolve())})
        return result, frame

    def _write_raw(self, out: Path, payload: str) -> str:
        raw_dir = out / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "understat_real_snapshot_raw.json"
        raw_path.write_text(payload, encoding="utf-8")
        return str(raw_path.resolve())

    def _blocked(self, status: str, notes: str = "") -> UnderstatRealSnapshotSmokeResult:
        return UnderstatRealSnapshotSmokeResult(
            real_snapshot_run_id="understat_real_snapshot_smoke_preview",
            provider="understat",
            source_id="",
            league=self.config.league,
            season=str(self.config.season),
            allow_network=bool(self.config.allow_network),
            network_calls_enabled=False,
            local_snapshot_input_path=str(self.config.local_snapshot or ""),
            raw_snapshot_path="",
            normalized_output_path="",
            manifest_path="",
            rows_raw=0,
            rows_normalized=0,
            rows_with_missing_required_values=0,
            rows_with_missing_optional_values=0,
            real_snapshot_status=status,
            recommendation=UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY if status == UNDERSTAT_REAL_SNAPSHOT_SMOKE_OFFLINE_READY else status,
            notes=notes or _notes(False, 0),
        )


def _safe_output_dir(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _resolve_optional(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe_path(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    if text.startswith(("http://", "https://")):
        return True
    return any(token in text for token in PROTECTED)


def _missing_rows(frame: pd.DataFrame, columns: list[str]) -> int:
    if frame.empty:
        return 0
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        mask = mask | frame[column].isna() | frame[column].astype(str).str.strip().eq("")
    return int(mask.sum())


def _notes(network: bool, missing_optional: int) -> str:
    notes = [UNDERSTAT_REAL_SNAPSHOT_SMOKE_NETWORK_ENABLED_EXPLICITLY if network else UNDERSTAT_REAL_SNAPSHOT_SMOKE_NETWORK_DISABLED_BY_DEFAULT]
    if missing_optional:
        notes.append(UNDERSTAT_REAL_SNAPSHOT_SMOKE_OPTIONAL_VALUES_MISSING)
    notes.extend([UNDERSTAT_REAL_SNAPSHOT_SMOKE_NO_MODEL_INTEGRATION_BY_DESIGN, UNDERSTAT_REAL_SNAPSHOT_SMOKE_NO_BETTING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
