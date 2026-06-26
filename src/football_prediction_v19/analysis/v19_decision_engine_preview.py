# -*- coding: utf-8 -*-
"""Preview-only v1.9 analyst decision engine."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

V19_DECISION_ENGINE_PREVIEW_READY = "V19_DECISION_ENGINE_PREVIEW_READY"
V19_DECISION_ENGINE_BLOCKED_MISSING_INPUT = "V19_DECISION_ENGINE_BLOCKED_MISSING_INPUT"
V19_DECISION_ENGINE_BLOCKED_UNSAFE_PATH = "V19_DECISION_ENGINE_BLOCKED_UNSAFE_PATH"

PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class V19DecisionEngineConfig:
    context_human_input_path: str | Path | None = None
    market_movement_diagnostic_path: str | Path | None = None
    availability_diagnostic_path: str | Path | None = None
    player_form_diagnostic_path: str | Path | None = None
    tactical_matchup_diagnostic_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_decision_engine"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19DecisionEngineResult:
    v19_decision_engine_preview_status: str
    summary_output_path: str
    structural_edges_output_path: str
    market_family_output_path: str
    no_bet_matrix_output_path: str
    score_tree_output_path: str
    manifest_path: str
    evidence_readiness_score: int
    final_decision_preview: str
    strongest_analyst_lean: str
    secondary_counterweight: str
    recommendation_preview_enabled: bool
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19DecisionEngineRunner:
    def __init__(self, config: V19DecisionEngineConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19DecisionEngineResult:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or any(_unsafe(path) for path in [
            self.config.context_human_input_path,
            self.config.market_movement_diagnostic_path,
            self.config.availability_diagnostic_path,
            self.config.player_form_diagnostic_path,
            self.config.tactical_matchup_diagnostic_path,
        ] if path):
            return self._blocked(V19_DECISION_ENGINE_BLOCKED_UNSAFE_PATH)
        context_path = _resolve(self.config.context_human_input_path, self.base) or self.base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
        context = _read_first_row(context_path)
        if context is None:
            return self._blocked(V19_DECISION_ENGINE_BLOCKED_MISSING_INPUT)
        market = _read_first_row(_resolve(self.config.market_movement_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "market_movement_diagnostic" / "market_movement_diagnostic.csv") or {}
        availability = _read_first_row(_resolve(self.config.availability_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "availability_diagnostic" / "availability_diagnostic.csv") or {}
        player = _read_first_row(_resolve(self.config.player_form_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "player_form_diagnostic" / "player_form_diagnostic.csv") or {}
        tactical = _read_first_row(_resolve(self.config.tactical_matchup_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "tactical_matchup_diagnostic" / "tactical_matchup_diagnostic.csv") or {}

        score = _evidence_readiness_score(context)
        blockers = _remaining_blockers(context, market, availability, player, tactical)
        final_decision = _final_decision(score, blockers)
        strongest = "Atalanta structural edge, but no production recommendation"
        counterweight = "Lazio set-piece + xGA + shot volume"
        edges = _structural_edges(context)
        families = _market_family_read(context, blockers)
        no_bet = _no_bet_matrix(blockers)
        score_tree = _score_tree(context, blockers)
        summary = {
            "v19_decision_engine_preview_status": V19_DECISION_ENGINE_PREVIEW_READY,
            "match_date": _text(context, "match_date"),
            "competition": _text(context, "competition"),
            "season": _text(context, "season"),
            "home_team": _text(context, "home_team"),
            "away_team": _text(context, "away_team"),
            "evidence_readiness_score": score,
            "remaining_blockers": " | ".join(blockers),
            "structural_edges": " | ".join(row["edge"] for row in edges),
            "final_decision_preview": final_decision,
            "strongest_analyst_lean": strongest,
            "secondary_counterweight": counterweight,
            "recommendation_preview_enabled": True,
            "network_calls_enabled": False,
            "prediction_logic_enabled": False,
            "betting_logic_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        }

        out.mkdir(parents=True, exist_ok=True)
        summary_path = out / "v19_decision_engine_summary.csv"
        edges_path = out / "v19_decision_engine_structural_edges.csv"
        family_path = out / "v19_decision_engine_market_family_read.csv"
        no_bet_path = out / "v19_decision_engine_no_bet_matrix.csv"
        score_tree_path = out / "v19_decision_engine_score_tree.csv"
        manifest_path = out / "v19_decision_engine_manifest.csv"
        pd.DataFrame([summary]).to_csv(summary_path, index=False)
        pd.DataFrame(edges).to_csv(edges_path, index=False)
        pd.DataFrame(families).to_csv(family_path, index=False)
        pd.DataFrame(no_bet).to_csv(no_bet_path, index=False)
        pd.DataFrame(score_tree).to_csv(score_tree_path, index=False)
        result = V19DecisionEngineResult(
            V19_DECISION_ENGINE_PREVIEW_READY,
            str(summary_path.resolve()),
            str(edges_path.resolve()),
            str(family_path.resolve()),
            str(no_bet_path.resolve()),
            str(score_tree_path.resolve()),
            str(manifest_path.resolve()),
            score,
            final_decision,
            strongest,
            counterweight,
            True,
            False,
            False,
            False,
            False,
            False,
            V19_DECISION_ENGINE_PREVIEW_READY,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        return result

    def _blocked(self, status: str) -> V19DecisionEngineResult:
        return V19DecisionEngineResult(status, "", "", "", "", "", "", 0, "NO_BET_RECOMMENDED", "", "", False, False, False, False, False, False, status)


def _evidence_readiness_score(row: dict[str, object]) -> int:
    score = 0
    score += 15 if all(_has(row, c) for c in ["home_xg", "away_xg", "home_xga", "away_xga"]) else 0
    score += 15 if all(_has(row, c) for c in ["home_player_xg_total", "away_player_xg_total", "home_player_xa_total", "away_player_xa_total"]) else 0
    score += 15 if all(_has(row, c) for c in ["home_shots", "away_shots", "home_shots_on_target", "away_shots_on_target", "home_possession", "away_possession"]) else 0
    score += 10 if all(_has(row, c) for c in ["home_current_odds", "draw_current_odds", "away_current_odds"]) else 0
    score += 10 if all(_has(row, c) for c in ["home_lineup_confirmed", "away_lineup_confirmed"]) else 0
    score += 10 if all(_has(row, c) for c in ["home_set_piece_xg_ratio", "away_set_piece_xg_ratio"]) else 0
    score += 5 if _has(row, "tactical_matchup_score") else 0
    score += 5 if _has(row, "h2h_summary") else 0
    score += 10 if all(_has(row, c) for c in ["home_recent_matches", "away_recent_matches"]) else 0
    score += 5 if all(_has(row, c) for c in ["home_big_chances", "away_big_chances"]) else 0
    return min(score, 100)


def _remaining_blockers(row: dict[str, object], market: dict[str, object], availability: dict[str, object], player: dict[str, object], tactical: dict[str, object]) -> list[str]:
    blockers = []
    if not all(_has(row, c) for c in ["home_recent_matches", "away_recent_matches"]):
        blockers.append("Recent Form")
    if not all(_has(row, c) for c in ["home_big_chances", "away_big_chances", "home_big_chances_against", "away_big_chances_against"]):
        blockers.append("Big Chances")
    if _text(availability, "missing_availability_fields"):
        blockers.append("Full Availability Details")
    if any(not _has(row, c) for c in ["home_open_odds", "draw_open_odds", "away_open_odds", "home_closing_odds", "draw_closing_odds", "away_closing_odds"]):
        blockers.append("Opening/Closing Market")
    if any(not _has(row, c) for c in ["dnb_home_odds", "dnb_away_odds", "over_current_odds", "under_current_odds"]):
        blockers.append("DNB/OU Market")
    if any(not _has(row, c) for c in ["home_tackles", "away_tackles", "home_interceptions", "away_interceptions", "home_blocks", "away_blocks"]):
        blockers.append("Defensive Actions")
    if _text(tactical, "missing_tactical_fields"):
        blockers.append("Tactical Detail Notes")
    blockers.append("Conflicting evidence")
    blockers.append("Safety disabled productive betting")
    return blockers


def _structural_edges(row: dict[str, object]) -> list[dict[str, str]]:
    return [
        {"layer": "Team xG", "edge": "Atalanta attacking production edge", "strength": "STRONG", "interpretation": "Atalanta xG For and xG Diff are clearly stronger."},
        {"layer": "Player xG/xA", "edge": "Atalanta player production / creation edge", "strength": "STRONG", "interpretation": "Atalanta has the stronger individual production and creation base."},
        {"layer": "xGA", "edge": "Lazio xGA counterweight", "strength": "MEDIUM", "interpretation": "Lazio has the cleaner concession profile."},
        {"layer": "Set-piece", "edge": "Lazio set-piece edge", "strength": "STRONG", "interpretation": "Lazio standards are the clearest home route."},
        {"layer": "Shots volume", "edge": "Lazio shot-volume counterweight", "strength": "MEDIUM", "interpretation": "Completion shows Lazio shot volume ahead."},
        {"layer": "SOT", "edge": "SOT balanced", "strength": "LOW", "interpretation": "Shots on target are level."},
        {"layer": "Market favorite", "edge": "Current odds make Atalanta market favorite", "strength": "MEDIUM", "interpretation": "Away current odds are shortest."},
    ]


def _market_family_read(row: dict[str, object], blockers: list[str]) -> list[dict[str, str]]:
    common = "Recommendation Preview only; production betting remains disabled."
    market_blockers = " | ".join([b for b in blockers if b in {"Opening/Closing Market", "DNB/OU Market", "Full Availability Details", "Recent Form", "Big Chances"}])
    return [
        {"market_family": "1X2", "status": "PARTIAL", "analyst_lean": "AWAY", "confidence_band": "MEDIUM", "reason": "Atalanta structural production edge, checked by Lazio counterweights. " + common, "blockers": market_blockers},
        {"market_family": "Double Chance", "status": "PARTIAL", "analyst_lean": "AWAY_OR_DRAW", "confidence_band": "MEDIUM", "reason": "Atalanta edge with draw/chaos risk from Lazio set pieces. " + common, "blockers": market_blockers},
        {"market_family": "DNB", "status": "BLOCKED", "analyst_lean": "AWAY", "confidence_band": "LOW", "reason": "DNB odds and full market context are incomplete.", "blockers": "DNB/OU Market | Opening/Closing Market"},
        {"market_family": "Goals / Over-Under", "status": "PARTIAL", "analyst_lean": "OVER_LEAN", "confidence_band": "LOW", "reason": "Both teams have plausible scoring routes, but recent form and big chances are missing.", "blockers": "Recent Form | Big Chances | DNB/OU Market"},
        {"market_family": "BTTS", "status": "PARTIAL", "analyst_lean": "BTTS_LEAN", "confidence_band": "LOW", "reason": "Atalanta production plus Lazio set-piece route supports a diagnostic BTTS lean only.", "blockers": "Recent Form | Big Chances | Full Availability Details"},
        {"market_family": "Score Family", "status": "PARTIAL", "analyst_lean": "NO_LEAN", "confidence_band": "LOW", "reason": "Score tree is readable, exact score remains blocked.", "blockers": "Recent Form | Big Chances | Tactical Detail Notes"},
        {"market_family": "No-Bet", "status": "NO_BET", "analyst_lean": "NO_LEAN", "confidence_band": "HIGH", "reason": "No production bet because stake/ROI/productive betting are disabled and gaps remain.", "blockers": "Safety disabled productive betting"},
    ]


def _no_bet_matrix(blockers: list[str]) -> list[dict[str, str]]:
    rows = [
        ("Missing recent form", "Recent Form", "HIGH", "prevents strong confidence", "yes"),
        ("Missing big chances", "Big Chances", "HIGH", "weakens goal and score-family read", "yes"),
        ("Missing full availability details", "Full Availability Details", "HIGH", "lineup status is not enough for production decision", "yes"),
        ("Missing opening/closing odds", "Opening/Closing Market", "MEDIUM", "blocks market movement validation", "yes"),
        ("Missing DNB/OU odds", "DNB/OU Market", "MEDIUM", "blocks family-specific market read", "yes"),
        ("Missing defensive actions", "Defensive Actions", "MEDIUM", "limits chaos/control confirmation", "no"),
        ("Missing tactical details", "Tactical Detail Notes", "MEDIUM", "limits matchup interpretation", "no"),
        ("Conflicting evidence", "Conflicting evidence", "MEDIUM", "Atalanta production vs Lazio set-piece/xGA/shots", "no"),
        ("Safety disabled productive betting", "Safety disabled productive betting", "CRITICAL", "production betting, stake and ROI are disabled", "yes"),
    ]
    active = set(blockers)
    return [{"check": label, "status": "ACTIVE" if key in active else "CLEAR", "severity": severity, "impact": impact, "blocks_recommendation": blocks, "blocks_stake": "always yes"} for label, key, severity, impact, blocks in rows]


def _score_tree(row: dict[str, object], blockers: list[str]) -> list[dict[str, str]]:
    common_blockers = "Recent Form | Big Chances | Full Availability Details"
    return [
        {"branch": "Low scoring", "score_examples": "0-0 / 1-0 / 0-1", "supporting_evidence": "Lazio xGA counterweight and incomplete recent-form confirmation.", "blockers": common_blockers, "probability_band": "LOW"},
        {"branch": "Balanced", "score_examples": "1-1 / 2-1 / 1-2", "supporting_evidence": "Atalanta production plus Lazio shot/SOT response and set-piece route.", "blockers": common_blockers, "probability_band": "MEDIUM"},
        {"branch": "Atalanta production", "score_examples": "1-2 / 0-2 / 2-2", "supporting_evidence": "Atalanta production supports away scoring route.", "blockers": common_blockers, "probability_band": "MEDIUM"},
        {"branch": "Lazio set-piece", "score_examples": "1-1 / 2-1 / 2-2", "supporting_evidence": "Lazio set-piece edge supports home goal route; shots/SOT make a home response plausible.", "blockers": common_blockers, "probability_band": "MEDIUM"},
        {"branch": "Draw/chaos", "score_examples": "1-1 / 2-2", "supporting_evidence": "Conflicting evidence creates draw/chaos branch.", "blockers": "Defensive Actions | Tactical Detail Notes", "probability_band": "LOW"},
    ]


def _final_decision(score: int, blockers: list[str]) -> str:
    critical_preview_blockers = {"Recent Form", "Big Chances", "Full Availability Details", "Opening/Closing Market", "DNB/OU Market"}
    if len(critical_preview_blockers.intersection(blockers)) >= 3:
        return "ANALYST_LEAN_ONLY" if score >= 50 else "NO_BET_RECOMMENDED"
    if score < 70:
        return "ANALYST_LEAN_ONLY" if score >= 50 else "NO_BET_RECOMMENDED"
    if score < 85:
        return "RECOMMENDATION_CANDIDATE"
    if any(b in blockers for b in ["Recent Form", "Big Chances", "Full Availability Details"]):
        return "RECOMMENDATION_CANDIDATE"
    return "STRONG_RECOMMENDATION_CANDIDATE"


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "v19_decision_engine").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _read_first_row(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists() or path.is_dir():
        return None
    try:
        frame = pd.read_csv(path, low_memory=False, keep_default_na=False)
    except (EmptyDataError, OSError):
        return None
    if frame.empty:
        return None
    return frame.iloc[0].to_dict()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _has(row: dict[str, object], column: str) -> bool:
    return not _blank(row.get(column, ""))


def _text(row: dict[str, object], column: str) -> str:
    value = row.get(column, "")
    return "" if _blank(value) else str(value)
