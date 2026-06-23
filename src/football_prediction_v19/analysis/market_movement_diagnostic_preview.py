# -*- coding: utf-8 -*-
"""Preview-only market movement diagnostic layer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from football_prediction_v19.analysis.odds_market_movement_input_preview import ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY

MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY = "MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY"
MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_MISSING_ODDS_INPUT = "MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_MISSING_ODDS_INPUT"
MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH = "MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH"
MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH = "MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH"
MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_UNSAFE_PATH = "MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_UNSAFE_PATH"
MARKET_MOVEMENT_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN = "MARKET_MOVEMENT_DIAGNOSTIC_NO_BETTING_OUTPUT_BY_DESIGN"
MARKET_MOVEMENT_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN = "MARKET_MOVEMENT_DIAGNOSTIC_NETWORK_DISABLED_BY_DESIGN"

OUTPUT_COLUMNS = [
    "match_date", "competition", "season", "home_team", "away_team", "cross_provider_match_key",
    "market_evidence_status", "market_movement_timing_flag",
    "home_odds_movement_direction", "draw_odds_movement_direction", "away_odds_movement_direction",
    "home_odds_movement_pct", "draw_odds_movement_pct", "away_odds_movement_pct",
    "favorite_side", "favorite_open_odds", "favorite_current_odds",
    "favorite_movement_direction", "favorite_movement_pct",
    "odds_availability_gate_status", "dnb_market_availability_status",
    "over_under_market_availability_status", "no_bet_market_safety_status",
    "missing_market_fields_count", "missing_market_fields", "market_diagnostic_notes",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "staking_logic_enabled", "roi_logic_enabled",
]
MANIFEST_COLUMNS = [
    "market_movement_diagnostic_run_id", "market_movement_diagnostic_status",
    "rows_diagnosed", "market_evidence_status", "market_movement_timing_flag",
    "odds_availability_gate_status", "dnb_market_availability_status",
    "over_under_market_availability_status", "no_bet_market_safety_status",
    "missing_market_fields_count", "output_path", "summary_path", "recommendation",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "staking_logic_enabled", "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class MarketMovementDiagnosticConfig:
    odds_market_movement_input_path: str | Path | None = None
    v19_diagnostic_gate_matrix_path: str | Path | None = None
    v19_diagnostic_synthesis_path: str | Path | None = None
    cross_provider_match_key: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/market_movement_diagnostic"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class MarketMovementDiagnosticResult:
    market_movement_diagnostic_run_id: str
    market_movement_diagnostic_status: str
    rows_diagnosed: int
    market_evidence_status: str
    market_movement_timing_flag: str
    odds_availability_gate_status: str
    dnb_market_availability_status: str
    over_under_market_availability_status: str
    no_bet_market_safety_status: str
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


class MarketMovementDiagnosticRunner:
    def __init__(self, config: MarketMovementDiagnosticConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> MarketMovementDiagnosticResult:
        out = _safe_output(self.config.output_dir, self.base)
        odds_path = _resolve(self.config.odds_market_movement_input_path, self.base)
        if out is None or (self.config.odds_market_movement_input_path is not None and _unsafe(self.config.odds_market_movement_input_path)) or (odds_path is not None and _unsafe(odds_path)):
            return self._blocked(MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_UNSAFE_PATH)
        if odds_path is None or not odds_path.exists():
            from scripts.build_odds_market_movement_input_preview import build_odds_market_movement_input_preview

            odds = build_odds_market_movement_input_preview(
                cross_provider_match_key=self.config.cross_provider_match_key or "u-bundesliga-2024-001",
                output_dir=self.base / "outputs" / "analysis_preview" / "odds_market_movement_input",
                base_dir=self.base,
            )
            if odds.get("odds_market_movement_input_status") != ODDS_MARKET_MOVEMENT_INPUT_PREVIEW_READY:
                return self._blocked(MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_MISSING_ODDS_INPUT)
            odds_path = Path(str(odds.get("output_path", "")))
        try:
            frame = pd.read_csv(odds_path, low_memory=False)
        except EmptyDataError:
            return self._blocked(MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_MISSING_ODDS_INPUT)
        selected = _select(frame, self.config.cross_provider_match_key)
        if selected.empty:
            return self._blocked(MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_UNKNOWN_MATCH)
        if len(selected) > 1:
            return self._blocked(MARKET_MOVEMENT_DIAGNOSTIC_BLOCKED_AMBIGUOUS_MATCH)
        row = selected.iloc[0]
        diagnostic = _diagnostic_row(row)
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "market_movement_diagnostic.csv"
        summary_path = out / "market_movement_diagnostic_summary.md"
        manifest_path = out / "market_movement_diagnostic_manifest.csv"
        pd.DataFrame([diagnostic], columns=OUTPUT_COLUMNS).to_csv(output_path, index=False)
        result = MarketMovementDiagnosticResult(
            "market_movement_diagnostic_preview", MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY,
            1, str(diagnostic["market_evidence_status"]), str(diagnostic["market_movement_timing_flag"]),
            str(diagnostic["odds_availability_gate_status"]), str(diagnostic["dnb_market_availability_status"]),
            str(diagnostic["over_under_market_availability_status"]), str(diagnostic["no_bet_market_safety_status"]),
            int(diagnostic["missing_market_fields_count"]), str(output_path.resolve()),
            str(summary_path.resolve()), str(manifest_path.resolve()),
            MARKET_MOVEMENT_DIAGNOSTIC_PREVIEW_READY, False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(
            "\n".join([
                "# Market Movement Diagnostic Preview", "",
                f"- market_movement_diagnostic_status: {result.market_movement_diagnostic_status}",
                f"- market_evidence_status: {result.market_evidence_status}",
                f"- market_movement_timing_flag: {result.market_movement_timing_flag}",
                f"- odds_availability_gate_status: {result.odds_availability_gate_status}",
                "- diagnostic-only market movement; missing odds remain missing",
                "- no production prediction, betting output, position sizing, or financial return tracking",
                "",
            ]),
            encoding="utf-8",
        )
        return result

    def _blocked(self, status: str) -> MarketMovementDiagnosticResult:
        return MarketMovementDiagnosticResult(
            "market_movement_diagnostic_preview", status, 0, "", "", "", "", "", "",
            0, "", "", "", status, False, False, False, False, False,
        )


def _diagnostic_row(row: pd.Series) -> dict[str, object]:
    missing_count = int(float(row.get("missing_market_fields_count", 0) or 0))
    closing_present = all(not _blank(row.get(c, "")) for c in ["home_closing_odds", "draw_closing_odds", "away_closing_odds"])
    evidence = "DIAGNOSTIC_READY" if missing_count == 0 else "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS"
    home = _movement(row.get("home_open_odds", ""), row.get("home_current_odds", ""))
    draw = _movement(row.get("draw_open_odds", ""), row.get("draw_current_odds", ""))
    away = _movement(row.get("away_open_odds", ""), row.get("away_current_odds", ""))
    favorite = _favorite(row)
    return {
        "match_date": row.get("match_date", ""), "competition": row.get("competition", ""),
        "season": row.get("season", ""), "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""), "cross_provider_match_key": row.get("cross_provider_match_key", ""),
        "market_evidence_status": evidence,
        "market_movement_timing_flag": "CURRENT_AND_CLOSING_AVAILABLE" if closing_present else "CURRENT_ONLY_PREVIEW",
        "home_odds_movement_direction": home[0], "draw_odds_movement_direction": draw[0],
        "away_odds_movement_direction": away[0], "home_odds_movement_pct": home[1],
        "draw_odds_movement_pct": draw[1], "away_odds_movement_pct": away[1],
        "favorite_side": favorite[0], "favorite_open_odds": favorite[1],
        "favorite_current_odds": favorite[2], "favorite_movement_direction": favorite[3],
        "favorite_movement_pct": favorite[4],
        "odds_availability_gate_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["home_current_odds", "draw_current_odds", "away_current_odds"]) else "DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA",
        "dnb_market_availability_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["dnb_home_odds", "dnb_away_odds"]) else "DIAGNOSTIC_GATE_REQUIRES_MARKET_DATA",
        "over_under_market_availability_status": "DIAGNOSTIC_READY" if all(not _blank(row.get(c, "")) for c in ["over_line", "over_current_odds", "under_current_odds"]) else "DIAGNOSTIC_GATE_REQUIRES_MARKET_DATA",
        "no_bet_market_safety_status": "BETTING_OUTPUT_DISABLED_BY_DESIGN",
        "missing_market_fields_count": missing_count,
        "missing_market_fields": row.get("missing_market_fields", ""),
        "market_diagnostic_notes": "Market movement diagnostic is for human review only; missing values were not inferred.",
        "network_calls_enabled": False, "prediction_logic_enabled": False,
        "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
    }


def _movement(open_value: object, current_value: object) -> tuple[str, object]:
    if _blank(open_value) or _blank(current_value):
        return "", ""
    open_float = float(open_value)
    current_float = float(current_value)
    pct = round(((current_float - open_float) / open_float) * 100, 2)
    if current_float < open_float:
        return "SHORTENED", pct
    if current_float > open_float:
        return "DRIFTED", pct
    return "UNCHANGED", pct


def _favorite(row: pd.Series) -> tuple[object, object, object, object, object]:
    candidates = []
    for side, open_col, current_col in [("HOME", "home_open_odds", "home_current_odds"), ("DRAW", "draw_open_odds", "draw_current_odds"), ("AWAY", "away_open_odds", "away_current_odds")]:
        if not _blank(row.get(current_col, "")):
            candidates.append((side, row.get(open_col, ""), float(row.get(current_col, ""))))
    if not candidates:
        return "", "", "", "", ""
    side, open_value, current_value = min(candidates, key=lambda item: item[2])
    direction, pct = _movement(open_value, current_value)
    return side, open_value, current_value, direction, pct


def _select(frame: pd.DataFrame, key: str | None) -> pd.DataFrame:
    if key and "cross_provider_match_key" in frame.columns:
        return frame[frame["cross_provider_match_key"].astype(str).str.lower() == str(key).lower()]
    return frame


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "market_movement_diagnostic").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    if str(path).strip() == "":
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
