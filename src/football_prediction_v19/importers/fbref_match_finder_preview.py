# -*- coding: utf-8 -*-
"""FBref match finder preview with deterministic local alias matching."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.provider_match_finder_preview import TeamAliasRegistryPreview

FBREF_MATCH_FINDER_PREVIEW_READY = "FBREF_MATCH_FINDER_PREVIEW_READY"
FBREF_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH = "FBREF_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH"
FBREF_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH = "FBREF_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH"
FBREF_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT = "FBREF_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT"
FBREF_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS = "FBREF_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS"
FBREF_MATCH_FINDER_BLOCKED_UNSAFE_PATH = "FBREF_MATCH_FINDER_BLOCKED_UNSAFE_PATH"
FBREF_MATCH_FINDER_NO_MODEL_INTEGRATION_BY_DESIGN = "FBREF_MATCH_FINDER_NO_MODEL_INTEGRATION_BY_DESIGN"
FBREF_MATCH_FINDER_NO_BETTING_INTEGRATION_BY_DESIGN = "FBREF_MATCH_FINDER_NO_BETTING_INTEGRATION_BY_DESIGN"

REQUIRED_COLUMNS = ["source_id", "provider", "provider_match_id", "competition", "season", "match_date", "home_team", "away_team"]
MANIFEST_COLUMNS = [
    "fbref_match_finder_run_id", "provider", "source_id", "provider_match_id",
    "cross_provider_match_key", "understat_provider_match_id", "competition",
    "season", "match_date", "home_team", "away_team", "selection_mode",
    "candidates_checked", "candidates_matched", "alias_match_used",
    "fbref_match_finder_status", "recommendation", "notes",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class FBrefMatchFinderConfig:
    normalized_input: str | Path | None = None
    provider_match_id: str | None = None
    understat_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    alias_registry: str | Path | None = None
    output_dir: str | Path = "outputs/provider_pull_preview/fbref/match_finder"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class FBrefMatchFinderResult:
    fbref_match_finder_run_id: str
    provider: str
    source_id: str
    provider_match_id: str
    cross_provider_match_key: str
    understat_provider_match_id: str
    competition: str
    season: str
    match_date: str
    home_team: str
    away_team: str
    selection_mode: str
    candidates_checked: int
    candidates_matched: int
    alias_match_used: bool
    fbref_match_finder_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    selected_match_output_path: str = ""
    manifest_path: str = ""
    summary_path: str = ""


class FBrefMatchFinderPreviewRunner:
    def __init__(self, config: FBrefMatchFinderConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[FBrefMatchFinderResult, pd.DataFrame]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(FBREF_MATCH_FINDER_BLOCKED_UNSAFE_PATH), pd.DataFrame()
        source = _resolve_input(self.config.normalized_input, self.base)
        alias_path = _resolve_optional(self.config.alias_registry, self.base)
        if _unsafe(source) or (alias_path is not None and _unsafe(alias_path)):
            return self._blocked(FBREF_MATCH_FINDER_BLOCKED_UNSAFE_PATH), pd.DataFrame()
        if not source.exists():
            return self._blocked(FBREF_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT), pd.DataFrame()
        frame = pd.read_csv(source, low_memory=False)
        missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            return self._blocked(FBREF_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS, candidates_checked=len(frame), notes=" | ".join(missing)), pd.DataFrame()
        selected = self._filter(frame)
        if len(selected) == 0:
            return self._blocked(FBREF_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH, candidates_checked=len(frame)), pd.DataFrame()
        if len(selected) > 1:
            return self._blocked(FBREF_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH, candidates_checked=len(frame), candidates_matched=len(selected)), pd.DataFrame()
        alias_used = bool(selected["_alias_match_used"].iloc[0])
        selected = selected.drop(columns=["_alias_match_used"])
        out.mkdir(parents=True, exist_ok=True)
        selected_path = out / "fbref_match_finder_selected_match.csv"
        manifest = out / "fbref_match_finder_manifest.csv"
        summary = out / "fbref_match_finder_summary.md"
        selected.to_csv(selected_path, index=False)
        result = self._result(FBREF_MATCH_FINDER_PREVIEW_READY, selected.iloc[0], len(frame), 1, alias_used, str(selected_path.resolve()), str(manifest.resolve()), str(summary.resolve()))
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest, index=False)
        summary.write_text(f"# FBref Match Finder Preview\n\n- fbref_match_finder_status: {result.fbref_match_finder_status}\n", encoding="utf-8")
        return result, selected

    def _filter(self, frame: pd.DataFrame) -> pd.DataFrame:
        filtered = frame.copy()
        if self.config.provider_match_id:
            filtered = filtered[filtered["provider_match_id"].astype(str) == str(self.config.provider_match_id)]
        if self.config.understat_provider_match_id:
            key = str(self.config.understat_provider_match_id)
            understat_ids = _series(filtered, "understat_provider_match_id")
            cross_keys = _series(filtered, "cross_provider_match_key")
            filtered = filtered[(understat_ids.astype(str) == key) | (cross_keys.astype(str) == key)]
        if self.config.competition:
            filtered = filtered[filtered["competition"].astype(str) == str(self.config.competition)]
        if self.config.season:
            filtered = filtered[filtered["season"].astype(str) == str(self.config.season)]
        if self.config.match_date:
            filtered = filtered[filtered["match_date"].astype(str).str[:10] == str(self.config.match_date)[:10]]
        if self.config.home_team or self.config.away_team:
            alias = TeamAliasRegistryPreview(_resolve_optional(self.config.alias_registry, self.base))
            rows = []
            for _, row in filtered.iterrows():
                used = False
                ok = True
                if self.config.home_team:
                    q, u, _ = alias.canonicalize(self.config.home_team, provider="fbref", league=str(row.get("competition", "")), season=str(row.get("season", "")))
                    used = used or u
                    ok = ok and q == _norm(row.get("home_team", ""))
                if self.config.away_team:
                    q, u, _ = alias.canonicalize(self.config.away_team, provider="fbref", league=str(row.get("competition", "")), season=str(row.get("season", "")))
                    used = used or u
                    ok = ok and q == _norm(row.get("away_team", ""))
                if ok:
                    r = row.copy()
                    r["_alias_match_used"] = used
                    rows.append(r)
            return pd.DataFrame(rows)
        filtered["_alias_match_used"] = False
        return filtered

    def _blocked(self, status: str, candidates_checked: int = 0, candidates_matched: int = 0, notes: str = "") -> FBrefMatchFinderResult:
        return FBrefMatchFinderResult("fbref_match_finder_preview", "fbref", "", self.config.provider_match_id or "", "", self.config.understat_provider_match_id or "", self.config.competition or "", self.config.season or "", self.config.match_date or "", "", "", _selection_mode(self.config), candidates_checked, candidates_matched, False, status, status, notes or _safety(), False, False, False)

    def _result(self, status: str, row: pd.Series, checked: int, matched: int, alias_used: bool, selected_path: str, manifest: str, summary: str) -> FBrefMatchFinderResult:
        return FBrefMatchFinderResult("fbref_match_finder_preview", "fbref", str(row.get("source_id", "")), str(row.get("provider_match_id", "")), str(row.get("cross_provider_match_key", "")), str(row.get("understat_provider_match_id", "")), str(row.get("competition", "")), str(row.get("season", "")), str(row.get("match_date", "")), str(row.get("home_team", "")), str(row.get("away_team", "")), _selection_mode(self.config), checked, matched, alias_used, status, status, _safety(), False, False, False, selected_path, manifest, summary)


def _resolve_input(path: str | Path | None, base: Path) -> Path:
    if path:
        p = Path(path)
        return (base / p).resolve() if not p.is_absolute() else p.resolve()
    d = base / "outputs" / "provider_pull_preview" / "fbref" / "normalized"
    matches = sorted(d.glob("fbref_provider_pull_normalized.csv"))
    return matches[0] if matches else d / "fbref_provider_pull_normalized.csv"


def _resolve_optional(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([""] * len(frame), index=frame.index)


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "provider_pull_preview" / "fbref" / "match_finder").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _selection_mode(config: FBrefMatchFinderConfig) -> str:
    if config.provider_match_id:
        return "provider_match_id"
    if config.understat_provider_match_id:
        return "understat_provider_match_id"
    return "team_names"


def _safety() -> str:
    return f"{FBREF_MATCH_FINDER_NO_MODEL_INTEGRATION_BY_DESIGN}; {FBREF_MATCH_FINDER_NO_BETTING_INTEGRATION_BY_DESIGN}"
