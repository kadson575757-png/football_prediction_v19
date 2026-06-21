# -*- coding: utf-8 -*-
"""Preview-only Understat + FBref match context bundle."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.provider_match_finder_preview import TeamAliasRegistryPreview

MATCH_CONTEXT_BUNDLE_PREVIEW_READY = "MATCH_CONTEXT_BUNDLE_PREVIEW_READY"
MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_UNDERSTAT_INPUT = "MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_UNDERSTAT_INPUT"
MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_FBREF_INPUT = "MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_FBREF_INPUT"
MATCH_CONTEXT_BUNDLE_BLOCKED_UNKNOWN_MATCH = "MATCH_CONTEXT_BUNDLE_BLOCKED_UNKNOWN_MATCH"
MATCH_CONTEXT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH = "MATCH_CONTEXT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH"
MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS = "MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS"
MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES = "MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES"
MATCH_CONTEXT_BUNDLE_BLOCKED_UNSAFE_PATH = "MATCH_CONTEXT_BUNDLE_BLOCKED_UNSAFE_PATH"
MATCH_CONTEXT_BUNDLE_OPTIONAL_VALUES_MISSING = "MATCH_CONTEXT_BUNDLE_OPTIONAL_VALUES_MISSING"
MATCH_CONTEXT_BUNDLE_NO_MODEL_INTEGRATION_BY_DESIGN = "MATCH_CONTEXT_BUNDLE_NO_MODEL_INTEGRATION_BY_DESIGN"
MATCH_CONTEXT_BUNDLE_NO_BETTING_INTEGRATION_BY_DESIGN = "MATCH_CONTEXT_BUNDLE_NO_BETTING_INTEGRATION_BY_DESIGN"
MATCH_CONTEXT_BUNDLE_NETWORK_DISABLED_BY_DESIGN = "MATCH_CONTEXT_BUNDLE_NETWORK_DISABLED_BY_DESIGN"

BUNDLE_COLUMNS = [
    "context_bundle_id", "source_id", "match_date", "competition", "season",
    "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id",
    "cross_provider_match_key", "understat_source_snapshot_path", "fbref_source_snapshot_path",
    "home_goals", "away_goals", "home_xg", "away_xg", "home_xga", "away_xga",
    "home_possession", "away_possession", "home_shots", "away_shots",
    "home_shots_on_target", "away_shots_on_target", "home_pass_completion_pct",
    "away_pass_completion_pct", "home_progressive_passes", "away_progressive_passes",
    "home_progressive_carries", "away_progressive_carries", "home_touches_att_pen_area",
    "away_touches_att_pen_area", "home_tackles", "away_tackles", "home_interceptions",
    "away_interceptions", "home_blocks", "away_blocks", "home_clearances",
    "away_clearances", "understat_data_quality_status", "fbref_data_quality_status",
    "context_data_quality_status", "missing_required_fields", "missing_optional_fields",
    "normalization_warning", "context_bundle_status", "recommendation", "notes",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
]
MANIFEST_COLUMNS = [
    "context_bundle_run_id", "understat_input_path", "fbref_input_path", "output_path",
    "rows_understat", "rows_fbref", "rows_joined", "candidates_checked",
    "candidates_matched", "missing_required_fields_count",
    "missing_optional_fields_count", "context_bundle_status", "recommendation",
    "notes", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
]
UNDERSTAT_REQUIRED = ["source_id", "provider_match_id", "league", "season", "match_date", "home_team", "away_team"]
FBREF_REQUIRED = ["source_id", "provider_match_id", "competition", "season", "match_date", "home_team", "away_team"]
OPTIONAL_FIELDS = [
    "home_xg", "away_xg", "home_xga", "away_xga", "home_possession", "away_possession",
    "home_shots", "away_shots", "home_shots_on_target", "away_shots_on_target",
    "home_pass_completion_pct", "away_pass_completion_pct", "home_progressive_passes",
    "away_progressive_passes", "home_progressive_carries", "away_progressive_carries",
    "home_touches_att_pen_area", "away_touches_att_pen_area", "home_tackles",
    "away_tackles", "home_interceptions", "away_interceptions", "home_blocks",
    "away_blocks", "home_clearances", "away_clearances",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class MatchContextBundleConfig:
    understat_normalized_input: str | Path | None = None
    fbref_normalized_input: str | Path | None = None
    provider_match_id: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    cross_provider_match_key: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    alias_registry: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/match_context_bundle"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class MatchContextBundleResult:
    context_bundle_run_id: str
    understat_input_path: str
    fbref_input_path: str
    output_path: str
    manifest_path: str
    summary_path: str
    rows_understat: int
    rows_fbref: int
    rows_joined: int
    candidates_checked: int
    candidates_matched: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    context_bundle_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    understat_provider_match_id: str = ""
    fbref_provider_match_id: str = ""
    cross_provider_match_key: str = ""
    home_team: str = ""
    away_team: str = ""
    match_date: str = ""


class MatchContextBundleRunner:
    def __init__(self, config: MatchContextBundleConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[MatchContextBundleResult, pd.DataFrame]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=BUNDLE_COLUMNS)
        understat_path = _resolve(self.config.understat_normalized_input, self.base)
        fbref_path = _resolve(self.config.fbref_normalized_input, self.base)
        alias_path = _resolve_optional(self.config.alias_registry, self.base)
        if any(_unsafe(p) for p in [understat_path, fbref_path] if p is not None) or (alias_path is not None and _unsafe(alias_path)):
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=BUNDLE_COLUMNS)
        if understat_path is None or not understat_path.exists():
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_UNDERSTAT_INPUT), pd.DataFrame(columns=BUNDLE_COLUMNS)
        if fbref_path is None or not fbref_path.exists():
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_FBREF_INPUT, understat_path=understat_path), pd.DataFrame(columns=BUNDLE_COLUMNS)
        understat = pd.read_csv(understat_path, low_memory=False)
        fbref = pd.read_csv(fbref_path, low_memory=False)
        missing_columns = _missing_columns(understat, UNDERSTAT_REQUIRED) + _missing_columns(fbref, FBREF_REQUIRED)
        if missing_columns:
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS, understat_path=understat_path, fbref_path=fbref_path, rows_understat=len(understat), rows_fbref=len(fbref), notes=" | ".join(missing_columns)), pd.DataFrame(columns=BUNDLE_COLUMNS)
        missing_required_values = _missing_value_count(understat, UNDERSTAT_REQUIRED) + _missing_value_count(fbref, FBREF_REQUIRED)
        if missing_required_values:
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES, understat_path=understat_path, fbref_path=fbref_path, rows_understat=len(understat), rows_fbref=len(fbref), missing_required=missing_required_values), pd.DataFrame(columns=BUNDLE_COLUMNS)
        pairs = self._candidate_pairs(understat, fbref, alias_path)
        checked = len(understat) * len(fbref)
        if len(pairs) == 0:
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_UNKNOWN_MATCH, understat_path=understat_path, fbref_path=fbref_path, rows_understat=len(understat), rows_fbref=len(fbref), candidates_checked=checked), pd.DataFrame(columns=BUNDLE_COLUMNS)
        if len(pairs) > 1:
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH, understat_path=understat_path, fbref_path=fbref_path, rows_understat=len(understat), rows_fbref=len(fbref), candidates_checked=checked, candidates_matched=len(pairs)), pd.DataFrame(columns=BUNDLE_COLUMNS)
        bundle_row = _bundle_row(pairs[0][0], pairs[0][1])
        if bundle_row["missing_required_fields"]:
            return self._blocked(MATCH_CONTEXT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES, understat_path=understat_path, fbref_path=fbref_path, rows_understat=len(understat), rows_fbref=len(fbref), candidates_checked=checked, candidates_matched=1, missing_required=len(bundle_row["missing_required_fields"].split(" | "))), pd.DataFrame(columns=BUNDLE_COLUMNS)
        missing_optional = len([field for field in bundle_row["missing_optional_fields"].split(" | ") if field])
        if missing_optional:
            bundle_row["normalization_warning"] = MATCH_CONTEXT_BUNDLE_OPTIONAL_VALUES_MISSING
        bundle = pd.DataFrame([{**bundle_row, "context_bundle_status": MATCH_CONTEXT_BUNDLE_PREVIEW_READY, "recommendation": MATCH_CONTEXT_BUNDLE_PREVIEW_READY, "notes": _notes(), "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False}], columns=BUNDLE_COLUMNS)
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "match_context_bundle.csv"
        manifest_path = out / "match_context_bundle_manifest.csv"
        summary_path = out / "match_context_bundle_summary.md"
        bundle.to_csv(output_path, index=False)
        result = MatchContextBundleResult(
            context_bundle_run_id="match_context_bundle_preview",
            understat_input_path=str(understat_path.resolve()),
            fbref_input_path=str(fbref_path.resolve()),
            output_path=str(output_path.resolve()),
            manifest_path=str(manifest_path.resolve()),
            summary_path=str(summary_path.resolve()),
            rows_understat=len(understat),
            rows_fbref=len(fbref),
            rows_joined=1,
            candidates_checked=checked,
            candidates_matched=1,
            missing_required_fields_count=0,
            missing_optional_fields_count=missing_optional,
            context_bundle_status=MATCH_CONTEXT_BUNDLE_PREVIEW_READY,
            recommendation=MATCH_CONTEXT_BUNDLE_PREVIEW_READY,
            notes=_notes(),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            understat_provider_match_id=str(bundle_row["understat_provider_match_id"]),
            fbref_provider_match_id=str(bundle_row["fbref_provider_match_id"]),
            cross_provider_match_key=str(bundle_row["cross_provider_match_key"]),
            home_team=str(bundle_row["home_team"]),
            away_team=str(bundle_row["away_team"]),
            match_date=str(bundle_row["match_date"]),
        )
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(f"# Match Context Bundle Preview\n\n- context_bundle_status: {result.context_bundle_status}\n- rows_joined: 1\n", encoding="utf-8")
        return result, bundle

    def _candidate_pairs(self, understat: pd.DataFrame, fbref: pd.DataFrame, alias_path: Path | None) -> list[tuple[pd.Series, pd.Series]]:
        alias = TeamAliasRegistryPreview(alias_path)
        pairs: list[tuple[pd.Series, pd.Series]] = []
        for _, urow in understat.iterrows():
            if not _row_matches_understat_filters(urow, self.config, alias):
                continue
            for _, frow in fbref.iterrows():
                if _pair_matches(urow, frow, self.config, alias):
                    pairs.append((urow, frow))
        return pairs

    def _blocked(
        self,
        status: str,
        *,
        understat_path: Path | None = None,
        fbref_path: Path | None = None,
        rows_understat: int = 0,
        rows_fbref: int = 0,
        candidates_checked: int = 0,
        candidates_matched: int = 0,
        missing_required: int = 0,
        notes: str = "",
    ) -> MatchContextBundleResult:
        return MatchContextBundleResult(
            context_bundle_run_id="match_context_bundle_preview",
            understat_input_path=str(understat_path or self.config.understat_normalized_input or ""),
            fbref_input_path=str(fbref_path or self.config.fbref_normalized_input or ""),
            output_path="",
            manifest_path="",
            summary_path="",
            rows_understat=rows_understat,
            rows_fbref=rows_fbref,
            rows_joined=0,
            candidates_checked=candidates_checked,
            candidates_matched=candidates_matched,
            missing_required_fields_count=missing_required,
            missing_optional_fields_count=0,
            context_bundle_status=status,
            recommendation=status,
            notes=notes or _notes(),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
        )


def _row_matches_understat_filters(row: pd.Series, config: MatchContextBundleConfig, alias: TeamAliasRegistryPreview) -> bool:
    keys = [config.provider_match_id, config.understat_provider_match_id, config.cross_provider_match_key]
    if any(keys) and str(row.get("provider_match_id", "")) not in {str(k) for k in keys if k}:
        return False
    if config.match_date and str(row.get("match_date", ""))[:10] != str(config.match_date)[:10]:
        return False
    if config.competition and str(row.get("league", "")) != str(config.competition):
        return False
    if config.season and str(row.get("season", "")) != str(config.season):
        return False
    if config.home_team:
        query, _, _ = alias.canonicalize(config.home_team, provider="understat", league=str(row.get("league", "")), season=str(row.get("season", "")))
        if query != _norm(row.get("home_team", "")):
            return False
    if config.away_team:
        query, _, _ = alias.canonicalize(config.away_team, provider="understat", league=str(row.get("league", "")), season=str(row.get("season", "")))
        if query != _norm(row.get("away_team", "")):
            return False
    return True


def _pair_matches(urow: pd.Series, frow: pd.Series, config: MatchContextBundleConfig, alias: TeamAliasRegistryPreview) -> bool:
    understat_id = str(urow.get("provider_match_id", ""))
    fbref_id = str(frow.get("provider_match_id", ""))
    cross = str(frow.get("cross_provider_match_key", ""))
    fb_understat = str(frow.get("understat_provider_match_id", ""))
    if config.fbref_provider_match_id and fbref_id != str(config.fbref_provider_match_id):
        return False
    if config.provider_match_id and config.provider_match_id == fbref_id:
        return True
    explicit_keys = {str(k) for k in [config.provider_match_id, config.understat_provider_match_id, config.cross_provider_match_key] if k}
    if explicit_keys and not ({understat_id, cross, fb_understat} & explicit_keys):
        return False
    if not explicit_keys and not config.fbref_provider_match_id and understat_id not in {cross, fb_understat}:
        return False
    if str(urow.get("match_date", ""))[:10] != str(frow.get("match_date", ""))[:10]:
        return False
    if str(urow.get("season", "")) != str(frow.get("season", "")):
        return False
    if str(urow.get("league", "")) != str(frow.get("competition", "")):
        return False
    home_query, _, _ = alias.canonicalize(str(urow.get("home_team", "")), provider="fbref", league=str(frow.get("competition", "")), season=str(frow.get("season", "")))
    away_query, _, _ = alias.canonicalize(str(urow.get("away_team", "")), provider="fbref", league=str(frow.get("competition", "")), season=str(frow.get("season", "")))
    return home_query == _norm(frow.get("home_team", "")) and away_query == _norm(frow.get("away_team", ""))


def _bundle_row(urow: pd.Series, frow: pd.Series) -> dict[str, object]:
    row = {column: "" for column in BUNDLE_COLUMNS}
    row.update({
        "context_bundle_id": "match_context_bundle_preview",
        "source_id": "understat_fbref_context_bundle_preview",
        "match_date": str(urow.get("match_date", ""))[:10],
        "competition": urow.get("league", ""),
        "season": urow.get("season", ""),
        "home_team": urow.get("home_team", ""),
        "away_team": urow.get("away_team", ""),
        "understat_provider_match_id": urow.get("provider_match_id", ""),
        "fbref_provider_match_id": frow.get("provider_match_id", ""),
        "cross_provider_match_key": frow.get("cross_provider_match_key", "") or frow.get("understat_provider_match_id", ""),
        "understat_source_snapshot_path": urow.get("source_snapshot_path", ""),
        "fbref_source_snapshot_path": frow.get("source_snapshot_path", ""),
        "home_goals": urow.get("home_goals", ""),
        "away_goals": urow.get("away_goals", ""),
        "home_xg": urow.get("home_xg", ""),
        "away_xg": urow.get("away_xg", ""),
        "home_xga": urow.get("home_xga", ""),
        "away_xga": urow.get("away_xga", ""),
        "understat_data_quality_status": urow.get("data_quality_status", ""),
        "fbref_data_quality_status": frow.get("data_quality_status", ""),
        "context_data_quality_status": "MATCH_CONTEXT_BUNDLE_PREVIEW_ROW",
    })
    for field in OPTIONAL_FIELDS:
        if field not in row or str(row[field]).strip() == "":
            row[field] = frow.get(field, row.get(field, ""))
    required = ["context_bundle_id", "match_date", "competition", "season", "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id"]
    missing_required = [field for field in required if _blank(row.get(field, ""))]
    missing_optional = [field for field in OPTIONAL_FIELDS if _blank(row.get(field, ""))]
    warnings = [str(value) for value in [urow.get("normalization_warning", ""), frow.get("normalization_warning", "")] if not _blank(value)]
    row["missing_required_fields"] = " | ".join(missing_required)
    row["missing_optional_fields"] = " | ".join(missing_optional)
    row["normalization_warning"] = " | ".join(warnings)
    return row


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "match_context_bundle").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _resolve_optional(path: str | Path | None, base: Path) -> Path | None:
    return _resolve(path, base)


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _missing_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column not in frame.columns]


def _missing_value_count(frame: pd.DataFrame, columns: list[str]) -> int:
    if frame.empty:
        return 0
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        mask = mask | frame[column].isna() | frame[column].astype(str).str.strip().eq("")
    return int(mask.sum())


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _notes() -> str:
    return "; ".join([
        MATCH_CONTEXT_BUNDLE_NETWORK_DISABLED_BY_DESIGN,
        MATCH_CONTEXT_BUNDLE_NO_MODEL_INTEGRATION_BY_DESIGN,
        MATCH_CONTEXT_BUNDLE_NO_BETTING_INTEGRATION_BY_DESIGN,
    ])
