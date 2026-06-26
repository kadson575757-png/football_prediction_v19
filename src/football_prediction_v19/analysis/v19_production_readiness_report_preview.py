# -*- coding: utf-8 -*-
"""Readable production readiness gate report."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

V19_PRODUCTION_READINESS_REPORT_PREVIEW_READY = "V19_PRODUCTION_READINESS_REPORT_PREVIEW_READY"
V19_PRODUCTION_READINESS_REPORT_BLOCKED_MISSING_INPUT = "V19_PRODUCTION_READINESS_REPORT_BLOCKED_MISSING_INPUT"
V19_PRODUCTION_READINESS_REPORT_BLOCKED_UNSAFE_PATH = "V19_PRODUCTION_READINESS_REPORT_BLOCKED_UNSAFE_PATH"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class V19ProductionReadinessReportConfig:
    production_readiness_gate_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_analysis_suite"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19ProductionReadinessReportResult:
    v19_production_readiness_report_status: str
    production_readiness_report_path: str
    final_decision_class: str
    promotion_allowed: bool
    strong_promotion_allowed: bool
    conflict_score: str
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19ProductionReadinessReportRenderer:
    def __init__(self, config: V19ProductionReadinessReportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[V19ProductionReadinessReportResult, str]:
        out = _safe_output(self.config.output_dir, self.base)
        source = _resolve(self.config.production_readiness_gate_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_production_readiness_gate" / "v19_production_readiness_gate.csv"
        if out is None or _unsafe(source):
            return self._blocked(V19_PRODUCTION_READINESS_REPORT_BLOCKED_UNSAFE_PATH), ""
        gate = _read_first(source)
        if gate is None:
            return self._blocked(V19_PRODUCTION_READINESS_REPORT_BLOCKED_MISSING_INPUT), ""
        report = _render(gate)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "production_readiness_report.md"
        path.write_text(report, encoding="utf-8")
        result = V19ProductionReadinessReportResult(
            V19_PRODUCTION_READINESS_REPORT_PREVIEW_READY,
            str(path.resolve()),
            str(gate.get("final_decision_class", "")),
            _bool(gate.get("promotion_allowed", False)),
            _bool(gate.get("strong_promotion_allowed", False)),
            str(gate.get("conflict_score", "")),
            False,
            False,
            False,
            False,
            V19_PRODUCTION_READINESS_REPORT_PREVIEW_READY,
        )
        return result, report

    def _blocked(self, status: str) -> V19ProductionReadinessReportResult:
        return V19ProductionReadinessReportResult(status, "", "BLOCKED_MISSING_DATA", False, False, "CRITICAL", False, False, False, False, status)


def _render(gate: dict[str, object]) -> str:
    critical = _split(gate.get("critical_blockers", ""))
    rows = pd.DataFrame([
        {
            "blocker": blocker,
            "severity": "CRITICAL",
            "affected markets": "1X2 / DNB / Over/Under / BTTS / Score Family",
            "why it matters": "blocks promotion beyond analyst lean",
            "blocks promotion": "yes",
            "needed input": _needed_input(blocker),
        }
        for blocker in critical
    ])
    edge_rows = pd.DataFrame([
        {"edge/counterweight": "Atalanta production", "side": "Atalanta", "strength": "STRONG", "score impact": gate.get("edge_score", ""), "interpretation": "Atalanta has the strongest structural edge."},
        {"edge/counterweight": "Lazio xGA", "side": "Lazio", "strength": "MEDIUM", "score impact": gate.get("counterweight_score", ""), "interpretation": "Lazio has a real defensive counterweight."},
        {"edge/counterweight": "Lazio set pieces", "side": "Lazio", "strength": "STRONG", "score impact": gate.get("counterweight_score", ""), "interpretation": "Lazio set pieces prevent strong promotion."},
    ])
    market_rows = pd.DataFrame([
        {"market": "1X2", "current status": "PARTIAL", "promotion allowed": "no", "blocker": gate.get("critical_blockers", ""), "needed evidence": "recent form, availability, opening/closing odds"},
        {"market": "Double Chance", "current status": "PARTIAL", "promotion allowed": "no", "blocker": gate.get("critical_blockers", ""), "needed evidence": "same as 1X2 plus market movement"},
        {"market": "DNB", "current status": "BLOCKED", "promotion allowed": "no", "blocker": "missing DNB odds", "needed evidence": "DNB odds"},
        {"market": "Over/Under", "current status": "PARTIAL", "promotion allowed": "no", "blocker": "missing recent form / big chances / OU odds", "needed evidence": "OU line and recent conversion"},
        {"market": "BTTS", "current status": "PARTIAL", "promotion allowed": "no", "blocker": "missing big chances and availability", "needed evidence": "big chances and lineup details"},
        {"market": "Score Family", "current status": "PARTIAL", "promotion allowed": "no", "blocker": "exact score blocked", "needed evidence": "recent form, big chances, tactical details"},
    ])
    return "\n".join([
        "# v1.9 Production Readiness Gate Preview",
        "",
        "## 1. Final Gate Decision",
        "",
        f"- final_decision_class: {gate.get('final_decision_class', '')}",
        f"- readiness_score: {gate.get('readiness_score', '')}",
        f"- promotion_allowed: {str(gate.get('promotion_allowed', '')).lower()}",
        f"- strong_promotion_allowed: {str(gate.get('strong_promotion_allowed', '')).lower()}",
        "- no production bet",
        "",
        "## 2. Critical Blockers",
        "",
        _markdown_table(rows, ["blocker", "severity", "affected markets", "why it matters", "blocks promotion", "needed input"]),
        "",
        "## 3. Edge vs Counterweight Balance",
        "",
        _markdown_table(edge_rows, ["edge/counterweight", "side", "strength", "score impact", "interpretation"]),
        "",
        "## 4. Promotion Logic",
        "",
        "BET_CANDIDATE_PREVIEW is blocked while recent form, big chances, full availability, opening/closing market and DNB/OU markets are missing. STRONG_BET_CANDIDATE_PREVIEW is blocked by critical blockers and conflict score.",
        "",
        "## 5. Downgrade Logic",
        "",
        "Downgrade to NO_BET_RECOMMENDED if recent form or big chances favor Lazio, if market drifts against Atalanta, or if lineup uncertainty remains unresolved. CONFLICT_REVIEW applies if contradiction increases or safety is violated.",
        "",
        "## 6. Market-Specific Gate",
        "",
        _markdown_table(market_rows, ["market", "current status", "promotion allowed", "blocker", "needed evidence"]),
        "",
        "## 7. Lazio-Atalanta Current Read",
        "",
        f"Atalanta has the strongest structural edge. Lazio has real counterweights through xGA, set pieces and shot volume. Evidence readiness is high but not production-ready. Critical blockers prevent promotion beyond analyst lean. Final class: {gate.get('final_decision_class', '')}. No production bet.",
        "",
        "## 8. Safety Footer",
        "",
        "Preview only. Not betting advice. No stake. No ROI. No automatic betting. network_calls_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false.",
        "",
    ])


def _needed_input(blocker: str) -> str:
    if "recent" in blocker:
        return "recent 5 match xG for/against"
    if "big chances" in blocker:
        return "big chances for/against"
    if "availability" in blocker:
        return "goalkeeper, missing, suspended and doubtful players"
    if "opening" in blocker:
        return "opening and closing odds"
    if "DNB" in blocker or "OU" in blocker:
        return "DNB and Over/Under odds"
    return "manual review"


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "No rows available."
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("|", ",") for column in columns) + " |")
    return "\n".join(lines)


def _split(value: object) -> list[str]:
    return [part for part in str(value).split(" | ") if part]


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "v19_analysis_suite").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _read_first(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists() or path.is_dir():
        return None
    try:
        frame = pd.read_csv(path, low_memory=False, keep_default_na=False)
    except (EmptyDataError, OSError):
        return None
    return None if frame.empty else frame.iloc[0].to_dict()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)
