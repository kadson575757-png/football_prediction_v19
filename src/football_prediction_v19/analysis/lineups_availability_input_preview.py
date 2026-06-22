# -*- coding: utf-8 -*-
"""Preview-only lineups / injuries / suspensions input layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY = "LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY"
LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNKNOWN_MATCH = "LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNKNOWN_MATCH"
LINEUPS_AVAILABILITY_INPUT_BLOCKED_AMBIGUOUS_MATCH = "LINEUPS_AVAILABILITY_INPUT_BLOCKED_AMBIGUOUS_MATCH"
LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNSAFE_PATH = "LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNSAFE_PATH"
LINEUPS_AVAILABILITY_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS = "LINEUPS_AVAILABILITY_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"
LINEUPS_AVAILABILITY_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES = "LINEUPS_AVAILABILITY_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES"
LINEUPS_AVAILABILITY_INPUT_NETWORK_DISABLED_BY_DESIGN = "LINEUPS_AVAILABILITY_INPUT_NETWORK_DISABLED_BY_DESIGN"
LINEUPS_AVAILABILITY_INPUT_NO_BETTING_OUTPUT_BY_DESIGN = "LINEUPS_AVAILABILITY_INPUT_NO_BETTING_OUTPUT_BY_DESIGN"

REQUIRED_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team",
    "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key",
    "availability_snapshot_source", "availability_snapshot_timestamp",
]
AVAILABILITY_COLUMNS = [
    "home_lineup_status", "away_lineup_status", "home_formation", "away_formation",
    "home_goalkeeper_status", "away_goalkeeper_status", "home_defensive_line_status",
    "away_defensive_line_status", "home_main_scorer_status", "away_main_scorer_status",
    "home_missing_players", "away_missing_players", "home_suspended_players",
    "away_suspended_players", "home_doubtful_players", "away_doubtful_players",
    "home_key_absence_count", "away_key_absence_count",
]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + AVAILABILITY_COLUMNS + [
    "availability_data_quality_status", "missing_availability_fields_count",
    "missing_availability_fields", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "lineups_availability_input_run_id", "lineups_availability_input_status",
    "rows_written", "candidates_matched", "missing_availability_fields_count",
    "output_path", "summary_path", "recommendation", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class LineupsAvailabilityInputConfig:
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    availability_input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/lineups_availability_input"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class LineupsAvailabilityInputResult:
    lineups_availability_input_run_id: str
    lineups_availability_input_status: str
    rows_written: int
    candidates_matched: int
    missing_availability_fields_count: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class LineupsAvailabilityInputRunner:
    def __init__(self, config: LineupsAvailabilityInputConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> LineupsAvailabilityInputResult:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.availability_input_path, self.base)
        if out is None or (self.config.availability_input_path is not None and _unsafe(self.config.availability_input_path)) or (source is not None and _unsafe(source)):
            return self._blocked(LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNSAFE_PATH)
        frame = pd.read_csv(source, low_memory=False) if source else _fixture()
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing_columns:
            return self._blocked(LINEUPS_AVAILABILITY_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS)
        for column in AVAILABILITY_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        selected = _select(frame, self.config)
        if selected.empty:
            return self._blocked(LINEUPS_AVAILABILITY_INPUT_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(LINEUPS_AVAILABILITY_INPUT_BLOCKED_AMBIGUOUS_MATCH, candidates=len(selected))
        row = selected.iloc[[0]].copy()
        if any(_blank(row.iloc[0].get(c, "")) for c in REQUIRED_COLUMNS):
            return self._blocked(LINEUPS_AVAILABILITY_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES, candidates=1)
        missing_fields = [c for c in AVAILABILITY_COLUMNS if _blank(row.iloc[0].get(c, ""))]
        row["availability_data_quality_status"] = "AVAILABILITY_PREVIEW_READY" if not missing_fields else "AVAILABILITY_PREVIEW_READY_WITH_MISSING_OPTIONAL_FIELDS"
        row["missing_availability_fields_count"] = len(missing_fields)
        row["missing_availability_fields"] = " | ".join(missing_fields)
        for column in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
            row[column] = False
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "lineups_availability_input.csv"
        summary_path = out / "lineups_availability_input_summary.md"
        manifest_path = out / "lineups_availability_input_manifest.csv"
        row[OUTPUT_COLUMNS].to_csv(output_path, index=False)
        result = LineupsAvailabilityInputResult(
            "lineups_availability_input_preview", LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY,
            1, 1, len(missing_fields), str(output_path.resolve()), str(summary_path.resolve()),
            str(manifest_path.resolve()), LINEUPS_AVAILABILITY_INPUT_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(
            "\n".join([
                "# Lineups Availability Input Preview", "",
                f"- lineups_availability_input_status: {result.lineups_availability_input_status}",
                f"- rows_written: {result.rows_written}",
                f"- missing_availability_fields_count: {result.missing_availability_fields_count}",
                "- diagnostic-only availability input; missing player values are surfaced, not filled",
                "- no production prediction, betting output, position sizing, or financial return tracking",
                "",
            ]),
            encoding="utf-8",
        )
        return result

    def _blocked(self, status: str, *, candidates: int = 0) -> LineupsAvailabilityInputResult:
        return LineupsAvailabilityInputResult(
            "lineups_availability_input_preview", status, 0, candidates, 0, "", "", "",
            status, False, False, False, False, False,
        )


def _fixture() -> pd.DataFrame:
    return pd.DataFrame([{
        "match_date": "2024-08-24", "competition": "Bundesliga", "season": "2024",
        "home_team": "Bayer Leverkusen", "away_team": "RB Leipzig",
        "understat_provider_match_id": "u-bundesliga-2024-001",
        "fbref_provider_match_id": "fbref-bundesliga-2024-001",
        "cross_provider_match_key": "u-bundesliga-2024-001",
        "availability_snapshot_source": "local_deterministic_preview_fixture",
        "availability_snapshot_timestamp": "2024-08-24T09:30:00Z",
        "home_lineup_status": "PROJECTED", "away_lineup_status": "PROJECTED",
        "home_formation": "3-4-2-1", "away_formation": "4-2-3-1",
        "home_goalkeeper_status": "AVAILABLE", "away_goalkeeper_status": "AVAILABLE",
        "home_defensive_line_status": "FULL", "away_defensive_line_status": "ONE_ROTATION_RISK",
        "home_main_scorer_status": "AVAILABLE", "away_main_scorer_status": "DOUBTFUL",
        "home_missing_players": "none listed", "away_missing_players": "main scorer doubtful",
        "home_suspended_players": "none listed", "away_suspended_players": "none listed",
        "home_doubtful_players": "none listed", "away_doubtful_players": "main scorer",
        "home_key_absence_count": 0, "away_key_absence_count": 1,
    }, {
        "match_date": "2024-09-01", "competition": "Bundesliga", "season": "2024",
        "home_team": "Borussia Dortmund", "away_team": "Freiburg",
        "understat_provider_match_id": "u-bundesliga-2024-002",
        "fbref_provider_match_id": "fbref-bundesliga-2024-002",
        "cross_provider_match_key": "u-bundesliga-2024-002",
        "availability_snapshot_source": "local_deterministic_preview_fixture",
        "availability_snapshot_timestamp": "2024-09-01T09:30:00Z",
        "home_lineup_status": "PROJECTED", "away_lineup_status": "PROJECTED",
    }])


def _select(frame: pd.DataFrame, config: LineupsAvailabilityInputConfig) -> pd.DataFrame:
    selected = frame.copy()
    key = config.cross_provider_match_key
    if not any([key, config.understat_provider_match_id, config.fbref_provider_match_id, config.home_team, config.away_team, config.match_date, config.competition, config.season]):
        key = "u-bundesliga-2024-001"
    for column, value in [
        ("cross_provider_match_key", key), ("understat_provider_match_id", config.understat_provider_match_id),
        ("fbref_provider_match_id", config.fbref_provider_match_id), ("home_team", config.home_team),
        ("away_team", config.away_team), ("competition", config.competition), ("season", config.season),
    ]:
        if value and column in selected.columns:
            selected = selected[selected[column].astype(str).str.lower() == str(value).lower()]
    if config.match_date and "match_date" in selected.columns:
        selected = selected[selected["match_date"].astype(str).str[:10] == str(config.match_date)[:10]]
    return selected


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "lineups_availability_input").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""
