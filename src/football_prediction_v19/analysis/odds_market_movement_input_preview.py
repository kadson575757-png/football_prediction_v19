# -*- coding: utf-8 -*-
"""Preview-only odds / market movement input layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY = "ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY"
ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNKNOWN_MATCH = "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNKNOWN_MATCH"
ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_AMBIGUOUS_MATCH = "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_AMBIGUOUS_MATCH"
ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNSAFE_PATH = "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNSAFE_PATH"
ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS = "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"
ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES = "ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES"
ODDS_MARKET_MOVEMENT_INPUT_NETWORK_DISABLED_BY_DESIGN = "ODDS_MARKET_MOVEMENT_INPUT_NETWORK_DISABLED_BY_DESIGN"
ODDS_MARKET_MOVEMENT_INPUT_NO_BETTING_OUTPUT_BY_DESIGN = "ODDS_MARKET_MOVEMENT_INPUT_NO_BETTING_OUTPUT_BY_DESIGN"

REQUIRED_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team",
    "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key",
    "market_snapshot_source", "market_snapshot_timestamp",
    "home_open_odds", "draw_open_odds", "away_open_odds",
    "home_current_odds", "draw_current_odds", "away_current_odds",
]
OPTIONAL_MARKET_COLUMNS = [
    "home_closing_odds", "draw_closing_odds", "away_closing_odds", "over_line",
    "over_open_odds", "under_open_odds", "over_current_odds", "under_current_odds",
    "dnb_home_odds", "dnb_away_odds", "handicap_line", "handicap_home_odds",
    "handicap_away_odds",
]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_MARKET_COLUMNS + [
    "odds_data_quality_status", "missing_market_fields_count", "missing_market_fields",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "odds_market_movement_input_run_id", "odds_market_movement_input_status",
    "rows_written", "candidates_matched", "missing_market_fields_count",
    "output_path", "summary_path", "recommendation", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class OddsMarketMovementInputConfig:
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    odds_input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/odds_market_movement_input"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class OddsMarketMovementInputResult:
    odds_market_movement_input_run_id: str
    odds_market_movement_input_status: str
    rows_written: int
    candidates_matched: int
    missing_market_fields_count: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class OddsMarketMovementInputRunner:
    def __init__(self, config: OddsMarketMovementInputConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> OddsMarketMovementInputResult:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.odds_input_path, self.base)
        if out is None or (self.config.odds_input_path is not None and _unsafe(self.config.odds_input_path)) or (source is not None and _unsafe(source)):
            return self._blocked(ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNSAFE_PATH)
        frame = pd.read_csv(source, low_memory=False) if source else _fixture()
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing_columns:
            return self._blocked(ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS)
        for column in OPTIONAL_MARKET_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        selected = _select(frame, self.config)
        if selected.empty:
            return self._blocked(ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_AMBIGUOUS_MATCH, candidates=len(selected))
        row = selected.iloc[[0]].copy()
        if _empty_required(row):
            return self._blocked(ODDS_MARKET_MOVEMENT_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES, candidates=1)
        missing_fields = [c for c in OPTIONAL_MARKET_COLUMNS if _blank(row.iloc[0].get(c, ""))]
        row["odds_data_quality_status"] = "ODDS_PREVIEW_READY" if not missing_fields else "ODDS_PREVIEW_READY_WITH_MISSING_OPTIONAL_FIELDS"
        row["missing_market_fields_count"] = len(missing_fields)
        row["missing_market_fields"] = " | ".join(missing_fields)
        for column in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
            row[column] = False
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "odds_market_movement_input.csv"
        summary_path = out / "odds_market_movement_input_summary.md"
        manifest_path = out / "odds_market_movement_input_manifest.csv"
        row[OUTPUT_COLUMNS].to_csv(output_path, index=False)
        result = OddsMarketMovementInputResult(
            "odds_market_movement_input_preview", ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY,
            1, 1, len(missing_fields), str(output_path.resolve()), str(summary_path.resolve()),
            str(manifest_path.resolve()), ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(
            "\n".join([
                "# Odds Market Movement Input Preview", "",
                f"- odds_market_movement_input_status: {result.odds_market_movement_input_status}",
                f"- rows_written: {result.rows_written}",
                f"- missing_market_fields_count: {result.missing_market_fields_count}",
                "- diagnostic-only odds input; missing values are surfaced, not filled",
                "- no production prediction, betting output, position sizing, or financial return tracking",
                "",
            ]),
            encoding="utf-8",
        )
        return result

    def _blocked(self, status: str, *, candidates: int = 0) -> OddsMarketMovementInputResult:
        return OddsMarketMovementInputResult(
            "odds_market_movement_input_preview", status, 0, candidates, 0, "", "", "",
            status, False, False, False, False, False,
        )


def _fixture() -> pd.DataFrame:
    return pd.DataFrame([{
        "match_date": "2024-08-24", "competition": "Bundesliga", "season": "2024",
        "home_team": "Bayer Leverkusen", "away_team": "RB Leipzig",
        "understat_provider_match_id": "u-bundesliga-2024-001",
        "fbref_provider_match_id": "fbref-bundesliga-2024-001",
        "cross_provider_match_key": "u-bundesliga-2024-001",
        "market_snapshot_source": "local_deterministic_preview_fixture",
        "market_snapshot_timestamp": "2024-08-24T10:00:00Z",
        "home_open_odds": 2.10, "draw_open_odds": 3.40, "away_open_odds": 3.20,
        "home_current_odds": 1.95, "draw_current_odds": 3.50, "away_current_odds": 3.60,
        "home_closing_odds": 1.90, "draw_closing_odds": 3.55, "away_closing_odds": 3.80,
        "over_line": 2.5, "over_open_odds": 1.90, "under_open_odds": 1.95,
        "over_current_odds": 1.85, "under_current_odds": 2.00,
        "dnb_home_odds": 1.55, "dnb_away_odds": 2.45, "handicap_line": -0.25,
        "handicap_home_odds": 1.92, "handicap_away_odds": 1.98,
    }, {
        "match_date": "2024-09-01", "competition": "Bundesliga", "season": "2024",
        "home_team": "Borussia Dortmund", "away_team": "Freiburg",
        "understat_provider_match_id": "u-bundesliga-2024-002",
        "fbref_provider_match_id": "fbref-bundesliga-2024-002",
        "cross_provider_match_key": "u-bundesliga-2024-002",
        "market_snapshot_source": "local_deterministic_preview_fixture",
        "market_snapshot_timestamp": "2024-09-01T10:00:00Z",
        "home_open_odds": 1.80, "draw_open_odds": 3.70, "away_open_odds": 4.10,
        "home_current_odds": 1.85, "draw_current_odds": 3.60, "away_current_odds": 4.00,
    }])


def _select(frame: pd.DataFrame, config: OddsMarketMovementInputConfig) -> pd.DataFrame:
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


def _empty_required(frame: pd.DataFrame) -> bool:
    return any(_blank(frame.iloc[0].get(c, "")) for c in REQUIRED_COLUMNS)


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "odds_market_movement_input").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
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
