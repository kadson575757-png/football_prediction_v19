# -*- coding: utf-8 -*-
"""Deterministic provider match finder preview with local team aliases."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

PROVIDER_MATCH_FINDER_PREVIEW_READY = "PROVIDER_MATCH_FINDER_PREVIEW_READY"
PROVIDER_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT = "PROVIDER_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT"
PROVIDER_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS = "PROVIDER_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS"
PROVIDER_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH = "PROVIDER_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH"
PROVIDER_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH = "PROVIDER_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH"
PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH = "PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH"
PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING = "PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING"
PROVIDER_MATCH_FINDER_ALIAS_MATCH_USED = "PROVIDER_MATCH_FINDER_ALIAS_MATCH_USED"
PROVIDER_MATCH_FINDER_NETWORK_DISABLED_BY_DESIGN = "PROVIDER_MATCH_FINDER_NETWORK_DISABLED_BY_DESIGN"
PROVIDER_MATCH_FINDER_MODEL_DISABLED_BY_DESIGN = "PROVIDER_MATCH_FINDER_MODEL_DISABLED_BY_DESIGN"
PROVIDER_MATCH_FINDER_BETTING_DISABLED_BY_DESIGN = "PROVIDER_MATCH_FINDER_BETTING_DISABLED_BY_DESIGN"

REQUIRED_NORMALIZED_COLUMNS = ["source_id", "provider", "provider_match_id", "league", "season", "match_date", "home_team", "away_team"]
OPTIONAL_VALUE_COLUMNS = ["home_xg", "away_xg", "home_xga", "away_xga", "venue", "neutral_venue"]
MANIFEST_COLUMNS = [
    "match_finder_run_id", "provider", "source_id", "provider_match_id", "league", "season",
    "match_date", "home_team", "away_team", "normalized_input_path", "selected_match_output_path",
    "alias_registry_path", "candidates_checked", "candidates_matched", "alias_match_used",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "match_finder_status", "recommendation", "notes",
]
PROTECTED_PATH_TOKENS = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class ProviderMatchFinderConfig:
    normalized_input: str | Path | None = None
    provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    league: str | None = None
    season: str | None = None
    alias_registry: str | Path | None = None
    output_dir: str | Path = "outputs/provider_pull_preview/match_finder"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class ProviderMatchFinderResult:
    match_finder_run_id: str
    provider: str
    source_id: str
    provider_match_id: str
    league: str
    season: str
    match_date: str
    home_team: str
    away_team: str
    normalized_input_path: str
    selected_match_output_path: str
    manifest_path: str
    summary_path: str
    alias_registry_path: str
    candidates_checked: int
    candidates_matched: int
    alias_match_used: bool
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    match_finder_status: str
    recommendation: str
    notes: str


class TeamAliasRegistryPreview:
    def __init__(self, alias_path: str | Path | None = None) -> None:
        self.alias_path = Path(alias_path) if alias_path else None
        self.aliases: dict[tuple[str, str, str, str], str] = {}
        if self.alias_path:
            self.aliases = self._load(self.alias_path)

    def canonicalize(self, value: str, *, provider: str = "", league: str = "", season: str = "") -> tuple[str, bool, str]:
        normalized = normalize_team_name(value)
        for key in [(provider, league, season, normalized), (provider, league, "", normalized), (provider, "", "", normalized), ("", league, season, normalized), ("", "", "", normalized)]:
            if key in self.aliases:
                return normalize_team_name(self.aliases[key]), True, self.aliases[key]
        return normalized, False, ""

    def _load(self, path: Path) -> dict[tuple[str, str, str, str], str]:
        if not path.exists():
            return {}
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            frame = pd.DataFrame(data if isinstance(data, list) else data.get("aliases", []))
        else:
            frame = pd.read_csv(path, low_memory=False)
        aliases: dict[tuple[str, str, str, str], str] = {}
        for _, row in frame.iterrows():
            canonical = str(row.get("canonical_team_name", "")).strip()
            alias = str(row.get("alias", "")).strip()
            if not canonical or not alias:
                continue
            aliases[(str(row.get("provider", "")).strip(), str(row.get("league", "")).strip(), str(row.get("season", "")).strip(), normalize_team_name(alias))] = canonical
        return aliases


class ProviderMatchFinderPreview:
    def __init__(self, config: ProviderMatchFinderConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def find(self) -> tuple[ProviderMatchFinderResult, pd.DataFrame]:
        out = _safe_output_dir(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH), pd.DataFrame()
        source = _resolve_normalized_input(self.config.normalized_input, self.base)
        if source is None or _unsafe_path(source):
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT), pd.DataFrame()
        alias_path = _resolve_optional_path(self.config.alias_registry, self.base)
        if alias_path is not None and _unsafe_path(alias_path):
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH), pd.DataFrame()
        if not source.exists():
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT, normalized_input_path=str(source)), pd.DataFrame()
        try:
            frame = pd.read_csv(source, low_memory=False)
        except Exception as exc:
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT, normalized_input_path=str(source), notes=str(exc)), pd.DataFrame()
        missing = [column for column in REQUIRED_NORMALIZED_COLUMNS if column not in frame.columns]
        if missing:
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS, normalized_input_path=str(source), candidates_checked=len(frame), notes=" | ".join(missing)), pd.DataFrame()
        candidates = self._filter(frame, alias_path)
        if len(candidates) == 0:
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH, normalized_input_path=str(source), candidates_checked=len(frame)), pd.DataFrame()
        if len(candidates) > 1:
            return self._blocked(PROVIDER_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH, normalized_input_path=str(source), candidates_checked=len(frame), candidates_matched=len(candidates)), pd.DataFrame()
        selected = candidates.iloc[[0]].copy()
        alias_used = bool(selected["_alias_match_used"].iloc[0])
        selected = selected.drop(columns=[column for column in ["_alias_match_used"] if column in selected.columns])
        warning_parts = []
        if alias_used:
            warning_parts.append(PROVIDER_MATCH_FINDER_ALIAS_MATCH_USED)
        if _missing_optional_values(selected):
            warning_parts.append(PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING)
        selected["match_finder_status"] = PROVIDER_MATCH_FINDER_PREVIEW_READY
        selected["match_query_home_team"] = self.config.home_team or ""
        selected["match_query_away_team"] = self.config.away_team or ""
        selected["match_query_match_date"] = self.config.match_date or ""
        selected["match_query_provider_match_id"] = self.config.provider_match_id or ""
        selected["alias_match_used"] = alias_used
        selected["alias_home_team"] = self.config.home_team or ""
        selected["alias_away_team"] = self.config.away_team or ""
        selected["match_finder_warning"] = "; ".join(warning_parts)
        out.mkdir(parents=True, exist_ok=True)
        selected_path = out / "provider_match_finder_selected_match.csv"
        manifest_path = out / "provider_match_finder_manifest.csv"
        summary_path = out / "provider_match_finder_summary.md"
        selected.to_csv(selected_path, index=False)
        result = self._result(
            status=PROVIDER_MATCH_FINDER_PREVIEW_READY,
            normalized_input_path=str(source.resolve()),
            selected_match_output_path=str(selected_path.resolve()),
            manifest_path=str(manifest_path.resolve()),
            summary_path=str(summary_path.resolve()),
            alias_registry_path=str(alias_path.resolve()) if alias_path else "",
            candidates_checked=len(frame),
            candidates_matched=1,
            alias_match_used=alias_used,
            row=selected.iloc[0],
            notes="; ".join(warning_parts) or _safety_notes(),
        )
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(_markdown(result), encoding="utf-8")
        return result, selected

    def _filter(self, frame: pd.DataFrame, alias_path: Path | None) -> pd.DataFrame:
        filtered = frame.copy()
        if self.config.provider_match_id:
            filtered = filtered[filtered["provider_match_id"].astype(str) == str(self.config.provider_match_id)]
        if self.config.league:
            filtered = filtered[filtered["league"].astype(str) == str(self.config.league)]
        if self.config.season:
            filtered = filtered[filtered["season"].astype(str) == str(self.config.season)]
        if self.config.match_date:
            filtered = filtered[filtered["match_date"].astype(str).str[:10] == str(self.config.match_date)[:10]]
        if self.config.home_team or self.config.away_team:
            registry = TeamAliasRegistryPreview(alias_path)
            rows = []
            for _, row in filtered.iterrows():
                provider = str(row.get("provider", ""))
                league = str(row.get("league", ""))
                season = str(row.get("season", ""))
                alias_used = False
                ok = True
                if self.config.home_team:
                    query, used, _alias = registry.canonicalize(self.config.home_team, provider=provider, league=league, season=season)
                    alias_used = alias_used or used
                    ok = ok and query == normalize_team_name(str(row.get("home_team", "")))
                if self.config.away_team:
                    query, used, _alias = registry.canonicalize(self.config.away_team, provider=provider, league=league, season=season)
                    alias_used = alias_used or used
                    ok = ok and query == normalize_team_name(str(row.get("away_team", "")))
                if ok:
                    enriched = row.copy()
                    enriched["_alias_match_used"] = alias_used
                    rows.append(enriched)
            return pd.DataFrame(rows)
        filtered["_alias_match_used"] = False
        return filtered

    def _blocked(self, status: str, *, normalized_input_path: str = "", candidates_checked: int = 0, candidates_matched: int = 0, notes: str = "") -> ProviderMatchFinderResult:
        return self._result(status=status, normalized_input_path=normalized_input_path, candidates_checked=candidates_checked, candidates_matched=candidates_matched, notes=notes or _safety_notes())

    def _result(self, *, status: str, normalized_input_path: str = "", selected_match_output_path: str = "", manifest_path: str = "", summary_path: str = "", alias_registry_path: str = "", candidates_checked: int = 0, candidates_matched: int = 0, alias_match_used: bool = False, row: pd.Series | None = None, notes: str = "") -> ProviderMatchFinderResult:
        row = row if row is not None else pd.Series(dtype=object)
        return ProviderMatchFinderResult(
            match_finder_run_id="provider_match_finder_preview",
            provider=str(row.get("provider", "")),
            source_id=str(row.get("source_id", "")),
            provider_match_id=str(row.get("provider_match_id", self.config.provider_match_id or "")),
            league=str(row.get("league", self.config.league or "")),
            season=str(row.get("season", self.config.season or "")),
            match_date=str(row.get("match_date", self.config.match_date or "")),
            home_team=str(row.get("home_team", "")),
            away_team=str(row.get("away_team", "")),
            normalized_input_path=normalized_input_path,
            selected_match_output_path=selected_match_output_path,
            manifest_path=manifest_path,
            summary_path=summary_path,
            alias_registry_path=alias_registry_path,
            candidates_checked=candidates_checked,
            candidates_matched=candidates_matched,
            alias_match_used=alias_match_used,
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            match_finder_status=status,
            recommendation=status,
            notes=notes,
        )


def normalize_team_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _resolve_normalized_input(path: str | Path | None, base: Path) -> Path | None:
    if path is not None:
        candidate = Path(path)
        return (base / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    normalized_dir = base / "outputs" / "provider_pull_preview" / "understat" / "normalized"
    matches = sorted(normalized_dir.glob("*_normalized_preview.csv"))
    return matches[0] if matches else normalized_dir / "understat_provider_pull_normalized.csv"


def _resolve_optional_path(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    candidate = Path(path)
    return (base / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()


def _safe_output_dir(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "provider_pull_preview" / "match_finder").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _unsafe_path(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    if text.startswith(("http://", "https://")):
        return True
    return any(token in text for token in PROTECTED_PATH_TOKENS)


def _missing_optional_values(frame: pd.DataFrame) -> bool:
    for column in OPTIONAL_VALUE_COLUMNS:
        if column not in frame.columns:
            return True
        if bool((frame[column].isna() | frame[column].astype(str).str.strip().eq("")).any()):
            return True
    return False


def _safety_notes() -> str:
    return f"{PROVIDER_MATCH_FINDER_NETWORK_DISABLED_BY_DESIGN}; {PROVIDER_MATCH_FINDER_MODEL_DISABLED_BY_DESIGN}; {PROVIDER_MATCH_FINDER_BETTING_DISABLED_BY_DESIGN}"


def _markdown(result: ProviderMatchFinderResult) -> str:
    return "\n".join([
        "# Provider Match Finder Preview",
        "",
        f"- match_finder_status: {result.match_finder_status}",
        f"- provider_match_id: {result.provider_match_id}",
        f"- candidates_matched: {result.candidates_matched}",
        "- no live network calls",
        "- no model predictions are run",
        "- no betting/staking recommendations are generated",
        "",
    ])
