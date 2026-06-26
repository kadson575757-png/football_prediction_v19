# -*- coding: utf-8 -*-
"""Preview-only production readiness gate for v1.9 analyst decisions."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

V19_PRODUCTION_READINESS_GATE_PREVIEW_READY = "V19_PRODUCTION_READINESS_GATE_PREVIEW_READY"
V19_PRODUCTION_READINESS_GATE_BLOCKED_MISSING_INPUT = "V19_PRODUCTION_READINESS_GATE_BLOCKED_MISSING_INPUT"
V19_PRODUCTION_READINESS_GATE_BLOCKED_UNSAFE_PATH = "V19_PRODUCTION_READINESS_GATE_BLOCKED_UNSAFE_PATH"

PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]
CRITICAL_NAMES = {
    "Recent Form": "missing recent form",
    "Big Chances": "missing big chances",
    "Full Availability Details": "missing full availability details",
    "Opening/Closing Market": "missing opening/closing odds",
    "DNB/OU Market": "missing DNB/OU odds",
    "Safety disabled productive betting": "productive betting safety disabled",
}


@dataclass(frozen=True)
class V19ProductionReadinessGateConfig:
    decision_engine_summary_path: str | Path | None = None
    structural_edges_path: str | Path | None = None
    market_family_path: str | Path | None = None
    no_bet_matrix_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_production_readiness_gate"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19ProductionReadinessGateResult:
    v19_production_readiness_gate_status: str
    production_readiness_output_path: str
    manifest_path: str
    final_decision_class: str
    readiness_score: int
    critical_blockers: str
    high_blockers: str
    medium_blockers: str
    edge_score: int
    counterweight_score: int
    conflict_score: str
    market_alignment_score: int
    confidence_score: int
    promotion_allowed: bool
    strong_promotion_allowed: bool
    downgrade_required: bool
    conflict_review_required: bool
    upgrade_conditions: str
    downgrade_conditions: str
    decision_explanation: str
    production_readiness_gate_enabled: bool
    decision_promotion_preview_enabled: bool
    recommendation_preview_enabled: bool
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19ProductionReadinessGateRunner:
    def __init__(self, config: V19ProductionReadinessGateConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19ProductionReadinessGateResult:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or any(_unsafe(path) for path in [self.config.decision_engine_summary_path, self.config.structural_edges_path, self.config.market_family_path, self.config.no_bet_matrix_path] if path):
            return self._blocked(V19_PRODUCTION_READINESS_GATE_BLOCKED_UNSAFE_PATH)
        summary_path = _resolve(self.config.decision_engine_summary_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_summary.csv"
        summary = _read_first(summary_path)
        if summary is None:
            return self._blocked(V19_PRODUCTION_READINESS_GATE_BLOCKED_MISSING_INPUT)
        edges = _read_frame(_resolve(self.config.structural_edges_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_structural_edges.csv")
        families = _read_frame(_resolve(self.config.market_family_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_market_family_read.csv")
        no_bet = _read_frame(_resolve(self.config.no_bet_matrix_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_no_bet_matrix.csv")

        readiness = int(summary.get("evidence_readiness_score", 0) or 0)
        blockers = [b for b in str(summary.get("remaining_blockers", "")).split(" | ") if b]
        critical = [CRITICAL_NAMES[b] for b in blockers if b in CRITICAL_NAMES]
        high = [row.get("check", "") for _, row in no_bet.iterrows() if str(row.get("status", "")) == "ACTIVE" and str(row.get("severity", "")) == "HIGH"]
        medium = [row.get("check", "") for _, row in no_bet.iterrows() if str(row.get("status", "")) == "ACTIVE" and str(row.get("severity", "")) == "MEDIUM"]
        edge_score = _edge_score(edges)
        counterweight_score = _counterweight_score(edges, blockers)
        market_alignment_score = 65 if "Current odds make Atalanta market favorite" in " | ".join(edges.get("edge", pd.Series(dtype=str)).astype(str)) else 35
        conflict_score = _conflict_score(edge_score, counterweight_score, critical)
        confidence_score = max(0, min(100, readiness + edge_score // 5 - counterweight_score // 5 - len(critical) * 4))
        final_class = _final_class(readiness, critical, conflict_score)
        promotion_allowed = final_class in {"BET_CANDIDATE_PREVIEW", "STRONG_BET_CANDIDATE_PREVIEW"}
        strong_allowed = final_class == "STRONG_BET_CANDIDATE_PREVIEW"
        conflict_review_required = conflict_score in {"CRITICAL"}
        downgrade_required = final_class in {"NO_BET_RECOMMENDED", "BLOCKED_MISSING_DATA", "CONFLICT_REVIEW"}
        upgrade_conditions = [
            "provide recent 5 match xG for/against for both teams",
            "provide big chances for/against",
            "provide full availability details",
            "provide goalkeeper status",
            "provide opening/closing odds",
            "provide DNB/OU odds if those markets are considered",
            "provide defensive actions and tactical detail notes",
        ]
        downgrade_conditions = [
            "Atalanta key attackers missing",
            "Lazio set-piece advantage confirmed even stronger",
            "market drifts against Atalanta",
            "recent form favors Lazio",
            "big chances favor Lazio",
            "Atalanta defensive concessions increase",
            "lineup uncertainty remains unresolved",
        ]
        explanation = (
            "Atalanta has the strongest structural edge, but Lazio counterweights and critical blockers prevent promotion beyond analyst lean. "
            "No production bet is created."
        )

        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "v19_production_readiness_gate.csv"
        manifest_path = out / "v19_production_readiness_gate_manifest.csv"
        result = V19ProductionReadinessGateResult(
            V19_PRODUCTION_READINESS_GATE_PREVIEW_READY,
            str(output_path.resolve()),
            str(manifest_path.resolve()),
            final_class,
            readiness,
            " | ".join(critical),
            " | ".join(high),
            " | ".join(medium),
            edge_score,
            counterweight_score,
            conflict_score,
            market_alignment_score,
            confidence_score,
            promotion_allowed,
            strong_allowed,
            downgrade_required,
            conflict_review_required,
            " | ".join(upgrade_conditions),
            " | ".join(downgrade_conditions),
            explanation,
            True,
            True,
            True,
            False,
            False,
            False,
            False,
            V19_PRODUCTION_READINESS_GATE_PREVIEW_READY,
        )
        pd.DataFrame([result.__dict__]).to_csv(output_path, index=False)
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        return result

    def _blocked(self, status: str) -> V19ProductionReadinessGateResult:
        return V19ProductionReadinessGateResult(status, "", "", "BLOCKED_MISSING_DATA", 0, "", "", "", 0, 0, "CRITICAL", 0, 0, False, False, True, True, "", "", status, False, False, False, False, False, False, False, status)


def _edge_score(edges: pd.DataFrame) -> int:
    text = " | ".join(edges.get("edge", pd.Series(dtype=str)).astype(str))
    score = 0
    score += 25 if "Atalanta attacking production edge" in text else 0
    score += 20 if "Atalanta player production / creation edge" in text else 0
    score += 15 if "Current odds make Atalanta market favorite" in text else 0
    score += 10 if "shot" in text.lower() and "Atalanta" in text else 0
    return min(score, 100)


def _counterweight_score(edges: pd.DataFrame, blockers: list[str]) -> int:
    text = " | ".join(edges.get("edge", pd.Series(dtype=str)).astype(str))
    score = 0
    score += 20 if "Lazio xGA counterweight" in text else 0
    score += 25 if "Lazio set-piece edge" in text else 0
    score += 15 if "Lazio shot-volume counterweight" in text else 0
    score += 10 if "SOT balanced" in text else 0
    score += 10 if "Opening/Closing Market" in blockers else 0
    score += 10 if "Full Availability Details" in blockers else 0
    score += 10 if "Recent Form" in blockers or "Big Chances" in blockers else 0
    return min(score, 100)


def _conflict_score(edge_score: int, counterweight_score: int, critical: list[str]) -> str:
    if critical:
        return "HIGH"
    if edge_score >= 55 and counterweight_score >= 50:
        return "HIGH"
    if edge_score >= 45 and counterweight_score >= 35:
        return "MEDIUM_HIGH"
    return "LOW"


def _final_class(readiness: int, critical: list[str], conflict_score: str) -> str:
    if readiness < 60:
        return "BLOCKED_MISSING_DATA"
    if readiness < 70:
        return "ANALYST_LEAN_ONLY"
    if critical or conflict_score in {"HIGH", "CRITICAL"}:
        return "ANALYST_LEAN_ONLY"
    if readiness >= 85 and conflict_score == "LOW":
        return "STRONG_BET_CANDIDATE_PREVIEW"
    if readiness >= 70:
        return "BET_CANDIDATE_PREVIEW"
    return "NO_BET_RECOMMENDED"


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "v19_production_readiness_gate").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _read_frame(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists() or path.is_dir():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False, keep_default_na=False)
    except (EmptyDataError, OSError):
        return pd.DataFrame()


def _read_first(path: Path | None) -> dict[str, object] | None:
    frame = _read_frame(path)
    if frame.empty:
        return None
    return frame.iloc[0].to_dict()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)
