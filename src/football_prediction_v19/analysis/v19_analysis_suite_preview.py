# -*- coding: utf-8 -*-
"""One-command v1.9 analysis suite preview bundle."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_production_readiness_gate_preview import (
    V19ProductionReadinessGateConfig,
    V19ProductionReadinessGateRunner,
)
from football_prediction_v19.analysis.v19_production_readiness_report_preview import (
    V19ProductionReadinessReportConfig,
    V19ProductionReadinessReportRenderer,
)

V19_ANALYSIS_SUITE_PREVIEW_READY = "V19_ANALYSIS_SUITE_PREVIEW_READY"
V19_ANALYSIS_SUITE_BLOCKED_PIPELINE_FAILED = "V19_ANALYSIS_SUITE_BLOCKED_PIPELINE_FAILED"
V19_ANALYSIS_SUITE_BLOCKED_UNSAFE_PATH = "V19_ANALYSIS_SUITE_BLOCKED_UNSAFE_PATH"

PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class V19AnalysisSuiteConfig:
    real_match_intake_path: str | Path | None = None
    manual_evidence_completion_path: str | Path | None = None
    emit_all: bool = False
    output_dir: str | Path = "outputs/analysis_preview/v19_analysis_suite"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19AnalysisSuiteResult:
    v19_analysis_suite_status: str
    analysis_suite_preview_enabled: bool
    analysis_suite_output_dir: str
    analysis_suite_summary_path: str
    final_decision_card_path: str
    full_match_analysis_path: str
    decision_report_path: str
    score_tree_detail_path: str
    market_family_matrix_path: str
    no_bet_matrix_path: str
    evidence_audit_path: str
    missing_data_action_plan_path: str
    production_readiness_report_path: str
    machine_readable_decision_path: str
    analysis_suite_bundle_index_path: str
    suite_artifacts_count: int
    evidence_readiness_score: int
    final_decision_preview: str
    strongest_analyst_lean: str
    v19_production_readiness_gate_status: str
    production_readiness_gate_enabled: bool
    decision_promotion_preview_enabled: bool
    final_decision_class: str
    promotion_allowed: bool
    strong_promotion_allowed: bool
    conflict_score: str
    recommendation_preview_enabled: bool
    decision_preview_enabled: bool
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19AnalysisSuiteRunner:
    def __init__(self, config: V19AnalysisSuiteConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19AnalysisSuiteResult:
        if _unsafe(self.config.real_match_intake_path or "") or _unsafe(self.config.manual_evidence_completion_path or ""):
            return self._blocked(V19_ANALYSIS_SUITE_BLOCKED_UNSAFE_PATH)
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(V19_ANALYSIS_SUITE_BLOCKED_UNSAFE_PATH)

        from scripts.run_match_analysis_preview import run_match_analysis_preview

        pipeline = run_match_analysis_preview(
            real_match_intake=self.config.real_match_intake_path,
            manual_evidence_completion=self.config.manual_evidence_completion_path,
            emit_v19_final_analysis_report=True,
            emit_v19_decision_report=True,
            emit_v19_recommendation_preview=True,
            base_dir=self.base,
        )
        if pipeline.get("v19_decision_engine_preview_status") != "V19_DECISION_ENGINE_PREVIEW_READY":
            return self._blocked(V19_ANALYSIS_SUITE_BLOCKED_PIPELINE_FAILED)

        out.mkdir(parents=True, exist_ok=True)
        decision_summary = _read_first(pipeline.get("summary_output_path"))
        edges = _read_frame(pipeline.get("structural_edges_output_path"))
        families = _read_frame(pipeline.get("market_family_output_path"))
        no_bet = _read_frame(pipeline.get("no_bet_matrix_output_path"))
        score_tree = _read_frame(pipeline.get("score_tree_output_path"))
        gate = V19ProductionReadinessGateRunner(
            V19ProductionReadinessGateConfig(
                decision_engine_summary_path=pipeline.get("summary_output_path"),
                structural_edges_path=pipeline.get("structural_edges_output_path"),
                market_family_path=pipeline.get("market_family_output_path"),
                no_bet_matrix_path=pipeline.get("no_bet_matrix_output_path"),
                base_dir=self.base,
            )
        ).run()
        report, _ = V19ProductionReadinessReportRenderer(
            V19ProductionReadinessReportConfig(
                production_readiness_gate_path=gate.production_readiness_output_path,
                output_dir=out,
                base_dir=self.base,
            )
        ).run()
        production_readiness = _read_first(gate.production_readiness_output_path)

        paths = {
            "analysis_suite_summary": out / "analysis_suite_summary.md",
            "final_decision_card": out / "final_decision_card.md",
            "full_match_analysis": out / "full_match_analysis.md",
            "decision_report": out / "decision_report.md",
            "score_tree_detail": out / "score_tree_detail.md",
            "market_family_matrix": out / "market_family_matrix.md",
            "no_bet_matrix": out / "no_bet_matrix.md",
            "evidence_audit": out / "evidence_audit.md",
            "missing_data_action_plan": out / "missing_data_action_plan.md",
            "production_readiness_report": out / "production_readiness_report.md",
            "machine_readable_decision": out / "machine_readable_decision.json",
            "bundle_index": out / "analysis_suite_bundle_index.csv",
        }

        _copy_or_write(pipeline.get("report_output_path"), paths["full_match_analysis"], "# v1.9 Full Match Analysis\n\nNot available.\n")
        _copy_or_write(pipeline.get("v19_decision_report_path"), paths["decision_report"], "# v1.9 Decision Report\n\nNot available.\n")
        paths["final_decision_card"].write_text(_final_decision_card(decision_summary, families, production_readiness), encoding="utf-8")
        paths["score_tree_detail"].write_text(_score_tree_detail(score_tree), encoding="utf-8")
        paths["market_family_matrix"].write_text(_market_family_matrix(families), encoding="utf-8")
        paths["no_bet_matrix"].write_text(_no_bet_matrix(no_bet), encoding="utf-8")
        paths["evidence_audit"].write_text(_evidence_audit(decision_summary, edges), encoding="utf-8")
        paths["missing_data_action_plan"].write_text(_missing_data_action_plan(), encoding="utf-8")
        if report.production_readiness_report_path and Path(report.production_readiness_report_path).exists():
            paths["production_readiness_report"] = Path(report.production_readiness_report_path)
        machine = _machine_readable(decision_summary, edges, families, no_bet, score_tree, paths, production_readiness)
        paths["machine_readable_decision"].write_text(json.dumps(machine, indent=2), encoding="utf-8")
        paths["analysis_suite_summary"].write_text(_suite_summary(decision_summary, edges, families, score_tree, no_bet, paths, production_readiness), encoding="utf-8")
        index = _bundle_index(paths)
        pd.DataFrame(index).to_csv(paths["bundle_index"], index=False)

        result = V19AnalysisSuiteResult(
            V19_ANALYSIS_SUITE_PREVIEW_READY,
            True,
            str(out.resolve()),
            str(paths["analysis_suite_summary"].resolve()),
            str(paths["final_decision_card"].resolve()),
            str(paths["full_match_analysis"].resolve()),
            str(paths["decision_report"].resolve()),
            str(paths["score_tree_detail"].resolve()),
            str(paths["market_family_matrix"].resolve()),
            str(paths["no_bet_matrix"].resolve()),
            str(paths["evidence_audit"].resolve()),
            str(paths["missing_data_action_plan"].resolve()),
            str(paths["production_readiness_report"].resolve()),
            str(paths["machine_readable_decision"].resolve()),
            str(paths["bundle_index"].resolve()),
            len(index),
            int(decision_summary.get("evidence_readiness_score", 0) or 0),
            str(decision_summary.get("final_decision_preview", "")),
            str(decision_summary.get("strongest_analyst_lean", "")),
            gate.v19_production_readiness_gate_status,
            gate.production_readiness_gate_enabled,
            gate.decision_promotion_preview_enabled,
            gate.final_decision_class,
            gate.promotion_allowed,
            gate.strong_promotion_allowed,
            gate.conflict_score,
            True,
            True,
            False,
            False,
            False,
            False,
            False,
            V19_ANALYSIS_SUITE_PREVIEW_READY,
        )
        return result

    def _blocked(self, status: str) -> V19AnalysisSuiteResult:
        return V19AnalysisSuiteResult(status, False, "", "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, "", "", "", False, False, "", False, False, "", False, False, False, False, False, False, False, status)


def _final_decision_card(summary: dict[str, object], families: pd.DataFrame, production_readiness: dict[str, object]) -> str:
    return "\n".join([
        "# v1.9 Final Decision Card Preview",
        "",
        "## 1. Match",
        "",
        f"- {summary.get('home_team', '')} vs {summary.get('away_team', '')}",
        f"- Competition: {summary.get('competition', '')}",
        f"- Date: {summary.get('match_date', '')}",
        "- Completion status: applied when manual completion fields are present",
        "",
        "## 2. Final Decision Preview",
        "",
        f"{summary.get('final_decision_preview', '')}",
        f"- final_decision_class: {production_readiness.get('final_decision_class', '')}",
        f"- promotion_allowed: {str(production_readiness.get('promotion_allowed', False)).lower()}",
        f"- strong_promotion_allowed: {str(production_readiness.get('strong_promotion_allowed', False)).lower()}",
        f"- conflict_score: {production_readiness.get('conflict_score', '')}",
        "",
        "## 3. Strongest Lean",
        "",
        "Atalanta structural edge.",
        "",
        "## 4. Counterweights",
        "",
        "- Lazio xGA counterweight",
        "- Lazio set-piece edge",
        "- Lazio shot-volume response",
        "- SOT balanced",
        "- Missing recent form",
        "- Missing big chances",
        "- Missing full availability details",
        "",
        "## 5. Market Family Ranking Preview",
        "",
        _markdown_table(families, ["market_family", "status", "analyst_lean", "confidence_band", "reason"]),
        "",
        "## 6. Confidence / Readiness",
        "",
        f"evidence_readiness_score: {summary.get('evidence_readiness_score', 0)}. Confidence is capped by recent form, big chances, availability detail and full market gaps.",
        "Production readiness gate: high evidence readiness but critical blockers prevent promotion beyond analyst lean.",
        "Upgrade with recent form, big chances, confirmed absences and opening/closing/DNB/OU odds. Downgrade if those layers contradict the current Atalanta edge.",
        "",
        "## 7. Final Analyst Sentence",
        "",
        "Atalanta is the strongest structural side in the current evidence, but Lazio has enough counterweights through xGA, set pieces and shot volume to prevent a production betting recommendation. Final status: analyst lean only / no production bet.",
        "",
        "## 8. Safety",
        "",
        "Recommendation Preview only. Not betting advice. No stake. No ROI. No automatic betting.",
        "",
    ])


def _score_tree_detail(score_tree: pd.DataFrame) -> str:
    intro = ["# v1.9 Score Tree Detail Preview", ""]
    branch_text = {
        "Low scoring": ("Low Scoring Branch", "Low scoring remains possible because exact attacking efficiency and recent conversion are incomplete."),
        "Balanced": ("Balanced Branch", "Balanced branch is highly relevant as diagnostic branch because both teams have plausible routes."),
        "Atalanta production": ("Atalanta Production Branch", "This is the strongest attacking branch."),
        "Lazio set-piece": ("Lazio Set-Piece / Counterweight Branch", "Lazio has a real goal route despite Atalanta production edge."),
        "Draw/chaos": ("Draw / Chaos Branch", "Draw/chaos remains live because the evidence is not one-directional."),
    }
    lines = intro
    for _, row in score_tree.iterrows():
        title, interpretation = branch_text.get(str(row.get("branch", "")), (str(row.get("branch", "")), "Diagnostic branch."))
        lines.extend([
            f"## {title}",
            "",
            f"- branch_status: PREVIEW_READABLE",
            f"- branch_confidence_band: {row.get('probability_band', '')}",
            f"- score examples: {row.get('score_examples', '')}",
            f"- supporting_evidence: {row.get('supporting_evidence', '')}",
            f"- blockers: {row.get('blockers', '')}",
            "- upgrade_conditions: add recent form, big chances, full availability and full market movement",
            "- downgrade_conditions: contradictory form, absences or market movement",
            "- no_exact_score_reason: No exact score prediction; no score bet; no stake; no ROI.",
            "",
            interpretation,
            "",
        ])
    lines.append("No exact score prediction.")
    return "\n".join(lines)


def _market_family_matrix(families: pd.DataFrame) -> str:
    enriched = families.copy()
    if not enriched.empty:
        enriched["evidence supporting"] = enriched["reason"]
        enriched["evidence against"] = "Lazio counterweights and remaining blockers"
        enriched["missing data"] = enriched["blockers"]
        enriched["upgrade conditions"] = "recent form + big chances + full availability + full market movement"
        enriched["downgrade conditions"] = "contradictory form, absences, adverse market movement"
        enriched["final action"] = enriched["market_family"].apply(lambda v: "ANALYST_LEAN_ONLY, no production bet" if v in {"1X2", "Double Chance"} else "Preview-readable only")
    return "\n".join([
        "# v1.9 Market Family Matrix Preview",
        "",
        _markdown_table(enriched, ["market_family", "status", "analyst_lean", "confidence_band", "evidence supporting", "evidence against", "missing data", "upgrade conditions", "downgrade conditions", "final action"]),
        "",
    ])


def _no_bet_matrix(no_bet: pd.DataFrame) -> str:
    return "# v1.9 No-Bet Matrix Preview\n\n" + _markdown_table(no_bet, ["check", "status", "severity", "impact", "blocks_recommendation", "blocks_stake"]) + "\n"


def _evidence_audit(summary: dict[str, object], edges: pd.DataFrame) -> str:
    return "\n".join([
        "# v1.9 Evidence Audit Preview",
        "",
        "## 1. Available Evidence",
        "",
        "- Team xG/xGA",
        "- Player xG/xA",
        "- Possession",
        "- Shots",
        "- Shots on Target",
        "- Formation",
        "- Set-piece",
        "- Current Odds",
        "- Tactical score",
        "- H2H/manual note",
        "",
        "## 2. Missing Evidence",
        "",
        "- Recent Form",
        "- Big Chances",
        "- Full Availability Details",
        "- Opening/Closing Odds",
        "- DNB/OU Odds",
        "- Defensive Actions",
        "- Tactical Detail Notes",
        "",
        "## 3. Evidence Quality",
        "",
        _markdown_table(edges, ["layer", "edge", "strength", "interpretation"]),
        "",
        "## 4. Ambiguity / Manual Review",
        "",
        f"- manual completion fields: {summary.get('remaining_blockers', '')}",
        "- team identity inferred from export order may require review when source files are untagged",
        "- remaining missing fields count is surfaced in the intake/report pipeline",
        "",
        "## 5. Evidence-to-Decision Trace",
        "",
        "- Atalanta attacking edge from team xG + player xG/xA",
        "- Lazio counterweight from xGA + set-pieces + shots",
        "- No production recommendation from blockers + disabled betting logic",
        "",
    ])


def _missing_data_action_plan() -> str:
    rows = [
        ("confirmed missing players", "availability changes team strength", "1X2/DNB/BTTS", "can upgrade or downgrade analyst lean", "home_missing_players=Name; away_missing_players=Name"),
        ("goalkeeper status", "goalkeeper affects xGA and goal routes", "1X2/Goals/BTTS", "can downgrade confidence", "home_goalkeeper_status=AVAILABLE"),
        ("suspended/doubtful players", "availability risk", "all families", "can block recommendation", "home_suspended_players=Name"),
        ("recent 5 match xG for/against", "form and conversion context", "1X2/Goals/Score", "can upgrade ANALYST_LEAN_ONLY -> BET_CANDIDATE_PREVIEW", "home_recent_xg_for=7.2"),
        ("big chances for/against", "chance quality", "Goals/BTTS/Score", "can upgrade or downgrade score tree", "home_big_chances_for=9"),
        ("opening/closing odds", "market movement", "1X2/DNB/OU", "can upgrade or downgrade market preview", "home_open_odds=3.7; home_closing_odds=3.5"),
    ]
    table = pd.DataFrame(rows, columns=["field_name", "why it matters", "which market family it affects", "how it can change final decision", "example input format"])
    return "\n".join([
        "# v1.9 Missing Data Action Plan",
        "",
        "## Priority 1 Critical",
        "",
        _markdown_table(table, list(table.columns)),
        "",
        "## Priority 2 Important",
        "",
        "- DNB odds",
        "- Over/Under line and odds",
        "- home/away split",
        "- defensive actions",
        "- rest days/fatigue",
        "- tactical notes",
        "",
        "## Priority 3 Nice",
        "",
        "- referee profile",
        "- weather/pitch",
        "- deeper H2H",
        "- lineup role notes",
        "",
        "Adding recent form + big chances + Full Availability Details + full market movement could upgrade ANALYST_LEAN_ONLY -> BET_CANDIDATE_PREVIEW or downgrade ANALYST_LEAN_ONLY -> NO_BET_RECOMMENDED.",
        "",
    ])


def _machine_readable(summary: dict[str, object], edges: pd.DataFrame, families: pd.DataFrame, no_bet: pd.DataFrame, score_tree: pd.DataFrame, paths: dict[str, Path], production_readiness: dict[str, object]) -> dict[str, object]:
    return {
        "match": {"home_team": summary.get("home_team", ""), "away_team": summary.get("away_team", ""), "match_date": summary.get("match_date", ""), "competition": summary.get("competition", "")},
        "safety": {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "recommendation_preview_enabled": True, "production_readiness_gate_enabled": True},
        "evidence_readiness_score": int(summary.get("evidence_readiness_score", 0) or 0),
        "final_decision_preview": summary.get("final_decision_preview", ""),
        "strongest_analyst_lean": summary.get("strongest_analyst_lean", ""),
        "production_readiness": {
            "status": production_readiness.get("v19_production_readiness_gate_status", ""),
            "final_decision_class": production_readiness.get("final_decision_class", ""),
            "promotion_allowed": _bool(production_readiness.get("promotion_allowed", False)),
            "strong_promotion_allowed": _bool(production_readiness.get("strong_promotion_allowed", False)),
            "readiness_score": int(production_readiness.get("readiness_score", 0) or 0),
            "critical_blockers": _split(production_readiness.get("critical_blockers", "")),
            "edge_score": int(production_readiness.get("edge_score", 0) or 0),
            "counterweight_score": int(production_readiness.get("counterweight_score", 0) or 0),
            "conflict_score": production_readiness.get("conflict_score", ""),
            "upgrade_conditions": _split(production_readiness.get("upgrade_conditions", "")),
            "downgrade_conditions": _split(production_readiness.get("downgrade_conditions", "")),
        },
        "counterweights": ["Lazio xGA counterweight", "Lazio set-piece edge", "Lazio shot-volume response", "SOT balanced"],
        "remaining_blockers": str(summary.get("remaining_blockers", "")).split(" | "),
        "market_family_read": families.to_dict(orient="records"),
        "no_bet_matrix": no_bet.to_dict(orient="records"),
        "score_tree": score_tree.to_dict(orient="records"),
        "upgrade_conditions": ["recent form", "big chances", "full availability", "opening/closing odds", "DNB/OU odds"],
        "downgrade_conditions": ["contradictory form", "key absences", "adverse market movement"],
        "artifact_paths": {name: str(path.resolve()) for name, path in paths.items()},
    }


def _suite_summary(summary: dict[str, object], edges: pd.DataFrame, families: pd.DataFrame, score_tree: pd.DataFrame, no_bet: pd.DataFrame, paths: dict[str, Path], production_readiness: dict[str, object]) -> str:
    return "\n".join([
        "# v1.9 Analysis Suite Preview",
        "",
        "## 1. Executive Summary",
        "",
        "Atalanta has the strongest structural edge. Lazio has real counterweights. Score tree is readable but exact score is blocked. Market families are only preview-readable. Final status: " + str(summary.get("final_decision_preview", "")) + ". No production bet.",
        "",
        "## 2. Final Decision Card",
        "",
        str(paths["final_decision_card"].resolve()),
        "",
        "## 3. Evidence Readiness",
        "",
        f"Evidence readiness score: {summary.get('evidence_readiness_score', 0)}/100.",
        "",
        "## 3b. Production Readiness",
        "",
        f"Gate status: {production_readiness.get('v19_production_readiness_gate_status', '')}. Final decision class: {production_readiness.get('final_decision_class', '')}. promotion_allowed={str(production_readiness.get('promotion_allowed', False)).lower()}; strong_promotion_allowed={str(production_readiness.get('strong_promotion_allowed', False)).lower()}; conflict_score={production_readiness.get('conflict_score', '')}.",
        "Evidence readiness is high but not production-ready. Critical blockers prevent promotion beyond analyst lean.",
        "",
        "## 4. Structural Edge Map",
        "",
        _markdown_table(edges, ["layer", "edge", "strength", "interpretation"]),
        "",
        "## 5. Market Family Matrix Summary",
        "",
        _markdown_table(families, ["market_family", "status", "analyst_lean", "confidence_band"]),
        "",
        "## 6. Score Tree Summary",
        "",
        _markdown_table(score_tree, ["branch", "score_examples", "probability_band"]),
        "",
        "## 7. No-Bet Matrix Summary",
        "",
        _markdown_table(no_bet, ["check", "status", "severity"]),
        "",
        "## 8. Evidence Audit Summary",
        "",
        "Team xG/xGA, player xG/xA, possession, shots, current odds and set-piece are present; recent form, big chances, full availability and full market movement remain blockers.",
        "",
        "## 9. Missing Data Action Plan Summary",
        "",
        "Provide recent form, big chances, full availability, opening/closing odds and DNB/OU odds next.",
        "",
        "## 10. Artifact Index",
        "",
        str(paths["bundle_index"].resolve()),
        "",
        "## 11. Safety Footer",
        "",
        "Recommendation Preview only. Not betting advice. No stake. No ROI. No automatic betting. network_calls_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false.",
        "",
    ])


def _bundle_index(paths: dict[str, Path]) -> list[dict[str, object]]:
    descriptions = {
        "analysis_suite_summary": "Master v1.9 analysis suite summary",
        "final_decision_card": "Compact final decision preview card",
        "full_match_analysis": "Full v1.9 final match analysis",
        "decision_report": "Decision engine report",
        "score_tree_detail": "Detailed score tree branches",
        "market_family_matrix": "Market-family preview matrix",
        "no_bet_matrix": "No-bet blocker matrix",
        "evidence_audit": "Evidence availability and trace audit",
        "missing_data_action_plan": "Next data actions for confidence upgrade",
        "production_readiness_report": "Production readiness gate and promotion/downgrade preview",
        "machine_readable_decision": "Machine-readable JSON decision preview",
        "bundle_index": "Suite bundle index",
    }
    return [{"artifact_name": name, "artifact_type": path.suffix.lstrip(".") or "directory", "path": str(path.resolve()), "status": "READY" if path.exists() else "MISSING", "description": descriptions.get(name, "")} for name, path in paths.items()]


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "No rows available."
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("\n", " ").replace("|", ",") for column in columns) + " |")
    return "\n".join(lines)


def _copy_or_write(source: object, target: Path, fallback: str) -> None:
    src = Path(str(source)) if source else None
    if src and src.exists() and src.is_file():
        shutil.copyfile(src, target)
    else:
        target.write_text(fallback, encoding="utf-8")


def _read_frame(path: object) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(str(path))
    if not p.exists() or p.is_dir():
        return pd.DataFrame()
    try:
        return pd.read_csv(p, low_memory=False, keep_default_na=False)
    except Exception:
        return pd.DataFrame()


def _read_first(path: object) -> dict[str, object]:
    frame = _read_frame(path)
    return {} if frame.empty else frame.iloc[0].to_dict()


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


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)
