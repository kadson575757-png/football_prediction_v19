# -*- coding: utf-8 -*-
"""Preview-only tactical / set-piece / fatigue input layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY = "TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY"
TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNKNOWN_MATCH = "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNKNOWN_MATCH"
TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_AMBIGUOUS_MATCH = "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_AMBIGUOUS_MATCH"
TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNSAFE_PATH = "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNSAFE_PATH"
TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS = "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"
TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES = "TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES"
TACTICAL_SET_PIECE_FATIGUE_INPUT_NETWORK_DISABLED_BY_DESIGN = "TACTICAL_SET_PIECE_FATIGUE_INPUT_NETWORK_DISABLED_BY_DESIGN"
TACTICAL_SET_PIECE_FATIGUE_INPUT_NO_BETTING_OUTPUT_BY_DESIGN = "TACTICAL_SET_PIECE_FATIGUE_INPUT_NO_BETTING_OUTPUT_BY_DESIGN"

REQUIRED_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team",
    "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key",
    "tactical_snapshot_source", "tactical_snapshot_timestamp",
]
TACTICAL_COLUMNS = [
    "home_set_piece_xg_for", "away_set_piece_xg_for",
    "home_set_piece_xg_against", "away_set_piece_xg_against",
    "home_set_piece_xg_ratio", "away_set_piece_xg_ratio",
    "tactical_matchup_score", "home_tactical_profile", "away_tactical_profile",
    "formation_matchup_note", "pressing_matchup_note", "transition_matchup_note",
    "defensive_line_risk_note", "home_rest_days", "away_rest_days",
    "home_travel_fatigue_note", "away_travel_fatigue_note",
    "do_so_fatigue_modifier", "xg_zone_correction_flag", "xg_zone_correction_note",
]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + TACTICAL_COLUMNS + [
    "tactical_data_quality_status", "missing_tactical_fields_count",
    "missing_tactical_fields", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "tactical_set_piece_fatigue_input_run_id", "tactical_set_piece_fatigue_input_status",
    "rows_written", "candidates_matched", "missing_tactical_fields_count",
    "output_path", "summary_path", "recommendation", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class TacticalSetPieceFatigueInputConfig:
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    tactical_input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/tactical_set_piece_fatigue_input"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class TacticalSetPieceFatigueInputResult:
    tactical_set_piece_fatigue_input_run_id: str
    tactical_set_piece_fatigue_input_status: str
    rows_written: int
    candidates_matched: int
    missing_tactical_fields_count: int
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class TacticalSetPieceFatigueInputRunner:
    def __init__(self, config: TacticalSetPieceFatigueInputConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> TacticalSetPieceFatigueInputResult:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.tactical_input_path, self.base)
        if out is None or (self.config.tactical_input_path is not None and _unsafe(self.config.tactical_input_path)) or (source is not None and _unsafe(source)):
            return self._blocked(TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNSAFE_PATH)
        frame = pd.read_csv(source, low_memory=False) if source else _fixture()
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing_columns:
            return self._blocked(TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS)
        for column in TACTICAL_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        selected = _select(frame, self.config)
        if selected.empty:
            return self._blocked(TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_AMBIGUOUS_MATCH, candidates=len(selected))
        row = selected.iloc[[0]].copy()
        if any(_blank(row.iloc[0].get(c, "")) for c in REQUIRED_COLUMNS):
            return self._blocked(TACTICAL_SET_PIECE_FATIGUE_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES, candidates=1)
        missing_fields = [c for c in TACTICAL_COLUMNS if _blank(row.iloc[0].get(c, ""))]
        row["tactical_data_quality_status"] = "TACTICAL_PREVIEW_READY" if not missing_fields else "TACTICAL_PREVIEW_READY_WITH_MISSING_OPTIONAL_FIELDS"
        row["missing_tactical_fields_count"] = len(missing_fields)
        row["missing_tactical_fields"] = " | ".join(missing_fields)
        for column in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
            row[column] = False
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "tactical_set_piece_fatigue_input.csv"
        summary_path = out / "tactical_set_piece_fatigue_input_summary.md"
        manifest_path = out / "tactical_set_piece_fatigue_input_manifest.csv"
        row[OUTPUT_COLUMNS].to_csv(output_path, index=False)
        result = TacticalSetPieceFatigueInputResult(
            "tactical_set_piece_fatigue_input_preview", TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY,
            1, 1, len(missing_fields), str(output_path.resolve()), str(summary_path.resolve()),
            str(manifest_path.resolve()), TACTICAL_SET_PIECE_FATIGUE_INPUT_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Tactical Set Piece Fatigue Input Preview", "",
            f"- tactical_set_piece_fatigue_input_status: {result.tactical_set_piece_fatigue_input_status}",
            f"- rows_written: {result.rows_written}",
            f"- missing_tactical_fields_count: {result.missing_tactical_fields_count}",
            "- diagnostic-only tactical evidence; missing values are surfaced, not filled",
            "- no production prediction, betting output, position sizing, or financial return tracking", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str, *, candidates: int = 0) -> TacticalSetPieceFatigueInputResult:
        return TacticalSetPieceFatigueInputResult(
            "tactical_set_piece_fatigue_input_preview", status, 0, candidates, 0, "", "", "",
            status, False, False, False, False, False,
        )


def _fixture() -> pd.DataFrame:
    return pd.DataFrame([{
        "match_date": "2024-08-24", "competition": "Bundesliga", "season": "2024",
        "home_team": "Bayer Leverkusen", "away_team": "RB Leipzig",
        "understat_provider_match_id": "u-bundesliga-2024-001",
        "fbref_provider_match_id": "fbref-bundesliga-2024-001",
        "cross_provider_match_key": "u-bundesliga-2024-001",
        "tactical_snapshot_source": "local_deterministic_preview_fixture",
        "tactical_snapshot_timestamp": "2024-08-24T10:15:00Z",
        "home_set_piece_xg_for": 0.42, "away_set_piece_xg_for": 0.31,
        "home_set_piece_xg_against": 0.22, "away_set_piece_xg_against": 0.39,
        "home_set_piece_xg_ratio": 1.91, "away_set_piece_xg_ratio": 0.79,
        "tactical_matchup_score": 7.4,
        "home_tactical_profile": "possession press with strong rest-defense",
        "away_tactical_profile": "vertical transition side",
        "formation_matchup_note": "home overloads half-spaces against away back four",
        "pressing_matchup_note": "home press can disrupt first progression line",
        "transition_matchup_note": "away transition threat remains visible",
        "defensive_line_risk_note": "home high line requires depth control",
        "home_rest_days": 6, "away_rest_days": 4,
        "home_travel_fatigue_note": "normal rest and no travel concern",
        "away_travel_fatigue_note": "shorter rest after away travel",
        "do_so_fatigue_modifier": "mild_away_fatigue",
        "xg_zone_correction_flag": "ZONE_CORRECTION_REVIEW_READY",
        "xg_zone_correction_note": "central box volume supports xG read",
    }, {
        "match_date": "2024-09-01", "competition": "Bundesliga", "season": "2024",
        "home_team": "Borussia Dortmund", "away_team": "Freiburg",
        "understat_provider_match_id": "u-bundesliga-2024-002",
        "fbref_provider_match_id": "fbref-bundesliga-2024-002",
        "cross_provider_match_key": "u-bundesliga-2024-002",
        "tactical_snapshot_source": "local_deterministic_preview_fixture",
        "tactical_snapshot_timestamp": "2024-09-01T10:15:00Z",
        "home_rest_days": 5, "away_rest_days": 5,
    }])


def _select(frame: pd.DataFrame, config: TacticalSetPieceFatigueInputConfig) -> pd.DataFrame:
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
    allowed = (base / "outputs" / "analysis_preview" / "tactical_set_piece_fatigue_input").resolve()
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
