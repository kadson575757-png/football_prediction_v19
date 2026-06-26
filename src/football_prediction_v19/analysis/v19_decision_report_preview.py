# -*- coding: utf-8 -*-
"""Readable v1.9 decision report preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

V19_DECISION_REPORT_PREVIEW_READY = "V19_DECISION_REPORT_PREVIEW_READY"
V19_DECISION_REPORT_BLOCKED_MISSING_INPUT = "V19_DECISION_REPORT_BLOCKED_MISSING_INPUT"
V19_DECISION_REPORT_BLOCKED_UNSAFE_PATH = "V19_DECISION_REPORT_BLOCKED_UNSAFE_PATH"

PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class V19DecisionReportConfig:
    decision_engine_summary_path: str | Path | None = None
    structural_edges_path: str | Path | None = None
    market_family_path: str | Path | None = None
    no_bet_matrix_path: str | Path | None = None
    score_tree_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_decision_report"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19DecisionReportResult:
    v19_decision_report_status: str
    v19_decision_report_path: str
    manifest_path: str
    evidence_readiness_score: int
    final_decision_preview: str
    strongest_analyst_lean: str
    recommendation_preview_enabled: bool
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19DecisionReportRenderer:
    def __init__(self, config: V19DecisionReportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[V19DecisionReportResult, str]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or any(_unsafe(path) for path in [
            self.config.decision_engine_summary_path,
            self.config.structural_edges_path,
            self.config.market_family_path,
            self.config.no_bet_matrix_path,
            self.config.score_tree_path,
        ] if path):
            return self._blocked(V19_DECISION_REPORT_BLOCKED_UNSAFE_PATH), ""
        summary_path = _resolve(self.config.decision_engine_summary_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_summary.csv"
        summary = _read_first_row(summary_path)
        if summary is None:
            return self._blocked(V19_DECISION_REPORT_BLOCKED_MISSING_INPUT), ""
        edges = _read_frame(_resolve(self.config.structural_edges_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_structural_edges.csv")
        families = _read_frame(_resolve(self.config.market_family_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_market_family_read.csv")
        no_bet = _read_frame(_resolve(self.config.no_bet_matrix_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_no_bet_matrix.csv")
        score_tree = _read_frame(_resolve(self.config.score_tree_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_decision_engine" / "v19_decision_engine_score_tree.csv")

        report = _render(summary, edges, families, no_bet, score_tree)
        out.mkdir(parents=True, exist_ok=True)
        report_path = out / "v19_decision_report_preview.md"
        manifest_path = out / "v19_decision_report_manifest.csv"
        report_path.write_text(report, encoding="utf-8")
        result = V19DecisionReportResult(
            V19_DECISION_REPORT_PREVIEW_READY,
            str(report_path.resolve()),
            str(manifest_path.resolve()),
            int(summary.get("evidence_readiness_score", 0) or 0),
            str(summary.get("final_decision_preview", "")),
            str(summary.get("strongest_analyst_lean", "")),
            True,
            False,
            False,
            False,
            False,
            False,
            V19_DECISION_REPORT_PREVIEW_READY,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        return result, report

    def _blocked(self, status: str) -> V19DecisionReportResult:
        return V19DecisionReportResult(status, "", "", 0, "NO_BET_RECOMMENDED", "", False, False, False, False, False, False, status)


def _render(summary: dict[str, object], edges: pd.DataFrame, families: pd.DataFrame, no_bet: pd.DataFrame, score_tree: pd.DataFrame) -> str:
    match = f"{summary.get('home_team', '')} vs {summary.get('away_team', '')}"
    lines = [
        "# v1.9 Decision Report Preview",
        "",
        "## 1. Decision Header",
        "",
        f"**Match:** {match} am {summary.get('match_date', '')} ({summary.get('competition', '')} {summary.get('season', '')}).",
        f"**Evidence readiness score:** {summary.get('evidence_readiness_score', 0)}/100.",
        f"**Final decision preview:** {summary.get('final_decision_preview', '')}.",
        f"**Strongest analyst lean:** {summary.get('strongest_analyst_lean', '')}.",
        "Recommendation Preview only, not betting advice, no stake, no ROI.",
        "",
        "## 2. Evidence Readiness",
        "",
        f"Score: {summary.get('evidence_readiness_score', 0)}/100. Present layers create an analyst-readable preview, but remaining blockers keep this away from production betting.",
        f"Remaining blockers: {summary.get('remaining_blockers', '')}.",
        "",
        "## 3. Structural Edge Map",
        "",
        _markdown_table(edges, ["layer", "edge", "strength", "interpretation"]),
        "",
        "## 4. Market Family Recommendation Preview",
        "",
        _markdown_table(families, ["market_family", "status", "analyst_lean", "confidence_band", "reason", "blockers"]),
        "",
        "## 5. No-Bet Matrix",
        "",
        _markdown_table(no_bet, ["check", "status", "severity", "impact", "blocks_recommendation", "blocks_stake"]),
        "",
        "## 6. Score Tree",
        "",
        _markdown_table(score_tree, ["branch", "score_examples", "supporting_evidence", "blockers", "probability_band"]),
        "",
        "## 7. Final Analyst Decision",
        "",
        "Atalanta has the strongest structural edge. Lazio has real counterweights through xGA, set pieces and shot volume. The safest decision is not a production betting recommendation.",
        "Analyst lean: Atalanta-side structural advantage, but no production bet. Score tree favors 'Atalanta can score + Lazio has a goal route', but exact score is blocked.",
        f"Final: {summary.get('final_decision_preview', '')}.",
        "",
        "## 8. Safety Footer",
        "",
        "Recommendation Preview only. Not betting advice. No stake. No ROI. No automatic betting.",
        "network_calls_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false.",
        "",
    ]
    return "\n".join(lines)


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "No rows available."
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("\n", " ") for column in columns) + " |")
    return "\n".join(lines)


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "v19_decision_report").resolve()
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


def _read_first_row(path: Path | None) -> dict[str, object] | None:
    frame = _read_frame(path)
    if frame.empty:
        return None
    return frame.iloc[0].to_dict()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)
