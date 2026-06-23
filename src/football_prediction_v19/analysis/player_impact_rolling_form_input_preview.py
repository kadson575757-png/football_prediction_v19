# -*- coding: utf-8 -*-
"""Preview-only player impact / rolling form input layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY = "PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY"
PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNKNOWN_MATCH = "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNKNOWN_MATCH"
PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_AMBIGUOUS_MATCH = "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_AMBIGUOUS_MATCH"
PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNSAFE_PATH = "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNSAFE_PATH"
PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS = "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"
PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES = "PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES"
PLAYER_IMPACT_ROLLING_FORM_INPUT_NETWORK_DISABLED_BY_DESIGN = "PLAYER_IMPACT_ROLLING_FORM_INPUT_NETWORK_DISABLED_BY_DESIGN"
PLAYER_IMPACT_ROLLING_FORM_INPUT_NO_BETTING_OUTPUT_BY_DESIGN = "PLAYER_IMPACT_ROLLING_FORM_INPUT_NO_BETTING_OUTPUT_BY_DESIGN"

REQUIRED_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team",
    "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key",
    "player_form_snapshot_source", "player_form_snapshot_timestamp",
]
PLAYER_FORM_COLUMNS = [
    "home_top_xg_player", "away_top_xg_player", "home_top_xg_value", "away_top_xg_value",
    "home_top_xa_player", "away_top_xa_player", "home_top_xa_value", "away_top_xa_value",
    "home_big_chances_for", "away_big_chances_for", "home_big_chances_against",
    "away_big_chances_against", "home_recent_matches", "away_recent_matches",
    "home_recent_goals_for", "away_recent_goals_for", "home_recent_goals_against",
    "away_recent_goals_against", "home_recent_xg_for", "away_recent_xg_for",
    "home_recent_xg_against", "away_recent_xg_against", "home_recent_conversion_note",
    "away_recent_conversion_note", "home_main_creator_status", "away_main_creator_status",
    "home_main_scorer_status", "away_main_scorer_status", "home_player_impact_note",
    "away_player_impact_note",
]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + PLAYER_FORM_COLUMNS + [
    "player_form_data_quality_status", "missing_player_form_fields_count",
    "missing_player_form_fields", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "player_impact_rolling_form_input_run_id", "player_impact_rolling_form_input_status",
    "rows_written", "candidates_matched", "missing_player_form_fields_count",
    "output_path", "summary_path", "recommendation", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class PlayerImpactRollingFormInputConfig:
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    player_form_input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/player_impact_rolling_form_input"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class PlayerImpactRollingFormInputResult:
    player_impact_rolling_form_input_run_id: str
    player_impact_rolling_form_input_status: str
    rows_written: int
    candidates_matched: int
    missing_player_form_fields_count: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class PlayerImpactRollingFormInputRunner:
    def __init__(self, config: PlayerImpactRollingFormInputConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> PlayerImpactRollingFormInputResult:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.player_form_input_path, self.base)
        if out is None or (self.config.player_form_input_path is not None and _unsafe(self.config.player_form_input_path)) or (source is not None and _unsafe(source)):
            return self._blocked(PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNSAFE_PATH)
        frame = pd.read_csv(source, low_memory=False) if source else _fixture()
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing_columns:
            return self._blocked(PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS)
        for column in PLAYER_FORM_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        selected = _select(frame, self.config)
        if selected.empty:
            return self._blocked(PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_AMBIGUOUS_MATCH, candidates=len(selected))
        row = selected.iloc[[0]].copy()
        if any(_blank(row.iloc[0].get(c, "")) for c in REQUIRED_COLUMNS):
            return self._blocked(PLAYER_IMPACT_ROLLING_FORM_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES, candidates=1)
        missing_fields = [c for c in PLAYER_FORM_COLUMNS if _blank(row.iloc[0].get(c, ""))]
        row["player_form_data_quality_status"] = "PLAYER_FORM_PREVIEW_READY" if not missing_fields else "PLAYER_FORM_PREVIEW_READY_WITH_MISSING_OPTIONAL_FIELDS"
        row["missing_player_form_fields_count"] = len(missing_fields)
        row["missing_player_form_fields"] = " | ".join(missing_fields)
        for column in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
            row[column] = False
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "player_impact_rolling_form_input.csv"
        summary_path = out / "player_impact_rolling_form_input_summary.md"
        manifest_path = out / "player_impact_rolling_form_input_manifest.csv"
        row[OUTPUT_COLUMNS].to_csv(output_path, index=False)
        result = PlayerImpactRollingFormInputResult(
            "player_impact_rolling_form_input_preview", PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY,
            1, 1, len(missing_fields), str(output_path.resolve()), str(summary_path.resolve()),
            str(manifest_path.resolve()), PLAYER_IMPACT_ROLLING_FORM_INPUT_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Player Impact Rolling Form Input Preview", "",
            f"- player_impact_rolling_form_input_status: {result.player_impact_rolling_form_input_status}",
            f"- rows_written: {result.rows_written}",
            f"- missing_player_form_fields_count: {result.missing_player_form_fields_count}",
            "- diagnostic-only player/form input; missing values are surfaced, not filled",
            "- no production prediction, betting output, position sizing, or financial return tracking", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str, *, candidates: int = 0) -> PlayerImpactRollingFormInputResult:
        return PlayerImpactRollingFormInputResult(
            "player_impact_rolling_form_input_preview", status, 0, candidates, 0, "", "", "",
            status, False, False, False, False, False,
        )


def _fixture() -> pd.DataFrame:
    return pd.DataFrame([{
        "match_date": "2024-08-24", "competition": "Bundesliga", "season": "2024",
        "home_team": "Bayer Leverkusen", "away_team": "RB Leipzig",
        "understat_provider_match_id": "u-bundesliga-2024-001",
        "fbref_provider_match_id": "fbref-bundesliga-2024-001",
        "cross_provider_match_key": "u-bundesliga-2024-001",
        "player_form_snapshot_source": "local_deterministic_preview_fixture",
        "player_form_snapshot_timestamp": "2024-08-24T09:45:00Z",
        "home_top_xg_player": "Home Striker", "away_top_xg_player": "Away Forward",
        "home_top_xg_value": 0.62, "away_top_xg_value": 0.48,
        "home_top_xa_player": "Home Creator", "away_top_xa_player": "Away Creator",
        "home_top_xa_value": 0.31, "away_top_xa_value": 0.27,
        "home_big_chances_for": 9, "away_big_chances_for": 6,
        "home_big_chances_against": 4, "away_big_chances_against": 7,
        "home_recent_matches": 5, "away_recent_matches": 5,
        "home_recent_goals_for": 11, "away_recent_goals_for": 8,
        "home_recent_goals_against": 5, "away_recent_goals_against": 7,
        "home_recent_xg_for": 9.8, "away_recent_xg_for": 7.1,
        "home_recent_xg_against": 5.2, "away_recent_xg_against": 7.9,
        "home_recent_conversion_note": "slight overconversion",
        "away_recent_conversion_note": "near xG expectation",
        "home_main_creator_status": "AVAILABLE", "away_main_creator_status": "AVAILABLE",
        "home_main_scorer_status": "AVAILABLE", "away_main_scorer_status": "DOUBTFUL",
        "home_player_impact_note": "top creator and scorer available",
        "away_player_impact_note": "main scorer doubtful in preview evidence",
    }, {
        "match_date": "2024-09-01", "competition": "Bundesliga", "season": "2024",
        "home_team": "Borussia Dortmund", "away_team": "Freiburg",
        "understat_provider_match_id": "u-bundesliga-2024-002",
        "fbref_provider_match_id": "fbref-bundesliga-2024-002",
        "cross_provider_match_key": "u-bundesliga-2024-002",
        "player_form_snapshot_source": "local_deterministic_preview_fixture",
        "player_form_snapshot_timestamp": "2024-09-01T09:45:00Z",
        "home_recent_matches": 5, "away_recent_matches": 5,
    }])


def _select(frame: pd.DataFrame, config: PlayerImpactRollingFormInputConfig) -> pd.DataFrame:
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
    allowed = (base / "outputs" / "analysis_preview" / "player_impact_rolling_form_input").resolve()
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
