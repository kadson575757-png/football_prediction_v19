# -*- coding: utf-8 -*-
"""Multi-match batch workbench preview for v1.9 analysis."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_batch_no_bet_review_preview import build_batch_no_bet_review
from football_prediction_v19.analysis.v19_candidate_shortlist_preview import build_candidate_shortlist
from football_prediction_v19.analysis.v19_market_family_portfolio_preview import build_market_family_portfolio
from football_prediction_v19.analysis.v19_match_workbench_preview import V19MatchWorkbenchConfig, V19MatchWorkbenchRunner
from football_prediction_v19.analysis.v19_missing_data_priority_board_preview import build_missing_data_priority_board
from football_prediction_v19.analysis.v19_portfolio_summary_preview import build_portfolio_summary

V19_BATCH_WORKBENCH_PREVIEW_READY = "V19_BATCH_WORKBENCH_PREVIEW_READY"
V19_BATCH_WORKBENCH_BLOCKED_MISSING_CONFIG = "V19_BATCH_WORKBENCH_BLOCKED_MISSING_CONFIG"


@dataclass(frozen=True)
class V19BatchWorkbenchConfig:
    batch_config: str | Path
    output_dir: str | Path = "outputs/analysis_preview/v19_batch_workbench"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19BatchWorkbenchResult:
    batch_workbench_status: str
    batch_workbench_enabled: bool
    portfolio_dashboard_enabled: bool
    candidate_shortlist_preview_enabled: bool
    batch_no_bet_review_enabled: bool
    batch_output_dir: str
    matches_total: int
    matches_succeeded: int
    matches_failed: int
    batch_dashboard_path: str
    portfolio_summary_path: str
    candidate_shortlist_path: str
    no_bet_review_path: str
    missing_data_priority_board_path: str
    market_family_portfolio_path: str
    readiness_ranking_path: str
    readiness_ranking_md_path: str
    batch_results_json_path: str
    batch_results_csv_path: str
    batch_bundle_index_path: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19BatchWorkbenchRunner:
    def __init__(self, config: V19BatchWorkbenchConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19BatchWorkbenchResult:
        config_path = _resolve(self.config.batch_config, self.base)
        if not config_path.exists():
            return self._blocked()
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        rows = pd.read_csv(config_path, keep_default_na=False).to_dict(orient="records")
        matches = []
        for row in rows:
            matches.append(self._run_match(row, out))
        succeeded = [m for m in matches if m.get("status") == "SUCCESS"]
        failed = [m for m in matches if m.get("status") != "SUCCESS"]
        paths = {
            "batch_dashboard": out / "batch_dashboard.md",
            "portfolio_summary": out / "portfolio_summary.md",
            "candidate_shortlist": out / "candidate_shortlist.md",
            "no_bet_review": out / "no_bet_review.md",
            "missing_data_priority_board": out / "missing_data_priority_board.md",
            "market_family_portfolio": out / "market_family_portfolio.md",
            "readiness_ranking": out / "readiness_ranking.csv",
            "readiness_ranking_md": out / "readiness_ranking.md",
            "batch_results_json": out / "batch_results.json",
            "batch_results_csv": out / "batch_results.csv",
            "batch_bundle_index": out / "batch_bundle_index.csv",
        }
        portfolio = build_portfolio_summary(matches, paths["portfolio_summary"])
        shortlist = build_candidate_shortlist(matches, paths["candidate_shortlist"])
        no_bet = build_batch_no_bet_review(matches, paths["no_bet_review"])
        priorities = build_missing_data_priority_board(matches, paths["missing_data_priority_board"])
        market = build_market_family_portfolio(matches, paths["market_family_portfolio"])
        ranking = _readiness_ranking(matches)
        pd.DataFrame(ranking).to_csv(paths["readiness_ranking"], index=False)
        paths["readiness_ranking_md"].write_text("# v1.9 Readiness Ranking\n\n" + _table(pd.DataFrame(ranking)) + "\n", encoding="utf-8")
        results = {
            "batch_workbench_status": V19_BATCH_WORKBENCH_PREVIEW_READY,
            "batch_config": str(config_path.resolve()),
            "matches_total": len(matches),
            "matches_succeeded": len(succeeded),
            "matches_failed": len(failed),
            "portfolio_summary": portfolio,
            "matches": matches,
            "safety": _safety(batch_workbench_enabled=True),
        }
        paths["batch_results_json"].write_text(json.dumps(results, indent=2), encoding="utf-8")
        pd.DataFrame(matches).to_csv(paths["batch_results_csv"], index=False)
        paths["batch_dashboard"].write_text(_dashboard(matches, portfolio, shortlist, no_bet, priorities, paths), encoding="utf-8")
        _write_bundle(paths["batch_bundle_index"], paths)
        return V19BatchWorkbenchResult(
            V19_BATCH_WORKBENCH_PREVIEW_READY,
            True,
            True,
            True,
            True,
            str(out.resolve()),
            len(matches),
            len(succeeded),
            len(failed),
            str(paths["batch_dashboard"].resolve()),
            str(paths["portfolio_summary"].resolve()),
            str(paths["candidate_shortlist"].resolve()),
            str(paths["no_bet_review"].resolve()),
            str(paths["missing_data_priority_board"].resolve()),
            str(paths["market_family_portfolio"].resolve()),
            str(paths["readiness_ranking"].resolve()),
            str(paths["readiness_ranking_md"].resolve()),
            str(paths["batch_results_json"].resolve()),
            str(paths["batch_results_csv"].resolve()),
            str(paths["batch_bundle_index"].resolve()),
            False,
            False,
            False,
            False,
            False,
            V19_BATCH_WORKBENCH_PREVIEW_READY,
        )

    def _run_match(self, row: dict[str, object], out: Path) -> dict[str, object]:
        required = ["match_id", "input_dir", "home_team", "away_team", "competition", "season", "match_date"]
        missing = [field for field in required if not str(row.get(field, "")).strip()]
        match_id = str(row.get("match_id", "missing_match_id") or "missing_match_id")
        match_dir = out / "matches" / _slug(match_id)
        match_dir.mkdir(parents=True, exist_ok=True)
        if missing:
            report = match_dir / "failed_match_report.md"
            report.write_text(f"# Failed Match Report\n\nMissing required fields: {', '.join(missing)}\n", encoding="utf-8")
            return {"match_id": match_id, "status": "FAILED", "error_message": "Missing required fields: " + ", ".join(missing), "artifact_paths": {"failed_match_report": str(report.resolve())}}
        try:
            workbench = V19MatchWorkbenchRunner(
                V19MatchWorkbenchConfig(
                    input_dir=row["input_dir"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    competition=row["competition"],
                    season=row["season"],
                    match_date=row["match_date"],
                    manual_evidence_completion=row.get("manual_evidence_completion", "") or None,
                    emit_all=True,
                    output_dir=match_dir,
                    base_dir=self.base,
                )
            ).run()
            machine = _read_json(Path(workbench.machine_readable_workbench_path))
            pr = machine.get("production_readiness", {})
            artifacts = _copy_match_artifacts(match_dir, workbench)
            market_statuses = _market_statuses(machine)
            blockers = pr.get("critical_blockers", [])
            return {
                "match_id": match_id,
                "status": "SUCCESS",
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "competition": row["competition"],
                "match_date": row["match_date"],
                "final_decision_class": pr.get("final_decision_class", ""),
                "evidence_readiness_score": pr.get("readiness_score", 0),
                "promotion_allowed": pr.get("promotion_allowed", False),
                "strong_promotion_allowed": pr.get("strong_promotion_allowed", False),
                "conflict_score": pr.get("conflict_score", ""),
                "critical_blockers": " | ".join(blockers),
                "critical_blockers_count": len(blockers),
                "strongest_analyst_lean": machine.get("analysis_suite", {}).get("strongest_analyst_lean", ""),
                "decision_explanation": pr.get("decision_explanation", "Critical data missing."),
                "market_family_statuses": market_statuses,
                "artifact_paths": artifacts,
            }
        except Exception as exc:
            report = match_dir / "failed_match_report.md"
            report.write_text(f"# Failed Match Report\n\n{exc}\n", encoding="utf-8")
            return {"match_id": match_id, "status": "FAILED", "error_message": str(exc), "artifact_paths": {"failed_match_report": str(report.resolve())}}

    def _blocked(self) -> V19BatchWorkbenchResult:
        return V19BatchWorkbenchResult(V19_BATCH_WORKBENCH_BLOCKED_MISSING_CONFIG, False, False, False, False, "", 0, 0, 0, "", "", "", "", "", "", "", "", "", "", "", False, False, False, False, False, V19_BATCH_WORKBENCH_BLOCKED_MISSING_CONFIG)


def _copy_match_artifacts(match_dir: Path, workbench: object) -> dict[str, str]:
    names = {
        "workbench_dashboard": workbench.workbench_dashboard_path,
        "machine_readable_workbench": workbench.machine_readable_workbench_path,
        "final_decision_card": workbench.final_decision_card_path,
        "production_readiness_report": workbench.production_readiness_report_path,
        "next_data_to_fill": workbench.next_data_to_fill_path,
        "completion_validation_report": workbench.completion_validation_report_path,
    }
    copied = {}
    for name, source_value in names.items():
        source = Path(str(source_value))
        if source.exists():
            target = match_dir / source.name
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)
            copied[name] = str(target.resolve())
    return copied


def _market_statuses(machine: dict[str, object]) -> dict[str, str]:
    records = machine.get("analysis_suite", {}).get("market_family_read", [])
    statuses = {str(row.get("market_family", "")): str(row.get("status", "")) for row in records if isinstance(row, dict)}
    if not statuses:
        statuses = {"1X2": "PARTIAL", "Double Chance": "PARTIAL", "DNB": "BLOCKED", "Over/Under": "PARTIAL", "BTTS": "PARTIAL", "Score Family": "PARTIAL", "No-Bet": "NO_BET"}
    return statuses


def _readiness_ranking(matches: list[dict[str, object]]) -> list[dict[str, object]]:
    success = sorted([m for m in matches if m.get("status") == "SUCCESS"], key=lambda m: -int(m.get("evidence_readiness_score", 0) or 0))
    rows = []
    for idx, match in enumerate(success, start=1):
        rows.append({
            "rank": idx,
            "match_id": match.get("match_id", ""),
            "home_team": match.get("home_team", ""),
            "away_team": match.get("away_team", ""),
            "final_decision_class": match.get("final_decision_class", ""),
            "evidence_readiness_score": match.get("evidence_readiness_score", 0),
            "conflict_score": match.get("conflict_score", ""),
            "promotion_allowed": match.get("promotion_allowed", False),
            "strong_promotion_allowed": match.get("strong_promotion_allowed", False),
            "critical_blockers_count": match.get("critical_blockers_count", 0),
            "missing_data_priority": "Recent Form, Big Chances, Availability, Market Movement",
            "recommended_next_action": "Fill Recent Form, Big Chances, Availability and Market Movement.",
        })
    return rows


def _dashboard(matches: list[dict[str, object]], portfolio: dict[str, object], shortlist: list[dict[str, object]], no_bet: list[dict[str, object]], priorities: list[dict[str, object]], paths: dict[str, Path]) -> str:
    overview = pd.DataFrame([{
        "match_id": m.get("match_id", ""),
        "match": f"{m.get('home_team', '')} vs {m.get('away_team', '')}",
        "competition": m.get("competition", ""),
        "date": m.get("match_date", ""),
        "final_decision_class": m.get("final_decision_class", ""),
        "evidence_readiness_score": m.get("evidence_readiness_score", ""),
        "promotion_allowed": m.get("promotion_allowed", ""),
        "strong_promotion_allowed": m.get("strong_promotion_allowed", ""),
        "conflict_score": m.get("conflict_score", ""),
        "top_blockers": m.get("critical_blockers", ""),
        "status": m.get("status", ""),
    } for m in matches])
    return "\n".join([
        "# v1.9 Batch Workbench Dashboard",
        "",
        "## 1. Batch Status",
        f"- batch_workbench_status: {V19_BATCH_WORKBENCH_PREVIEW_READY}",
        f"- matches_total: {len(matches)}",
        f"- matches_succeeded: {len([m for m in matches if m.get('status') == 'SUCCESS'])}",
        f"- matches_failed: {len([m for m in matches if m.get('status') != 'SUCCESS'])}",
        "- safety status: preview-only",
        "",
        "## 2. Match Overview",
        _table(overview),
        "",
        "## 3. Portfolio Read",
        f"- analyst lean only: {portfolio.get('analyst_lean_only_count', 0)}",
        f"- candidate preview: {portfolio.get('bet_candidate_preview_count', 0)}",
        f"- no-bet: {portfolio.get('no_bet_count', 0)}",
        "- matches need more data when promotion_allowed=false.",
        "",
        "## 4. Candidate Shortlist Preview",
        _table(pd.DataFrame(shortlist)),
        "",
        "## 5. No-Bet / Blocked Matches",
        _table(pd.DataFrame(no_bet)),
        "",
        "## 6. Missing Data Priorities",
        _table(pd.DataFrame(priorities)),
        "",
        "## 7. Artifact Links",
        *[f"- {name}: {path.resolve()}" for name, path in paths.items()],
        "",
        "## 8. Safety Footer",
        "no production betting; no stake; no ROI; no automatic betting; network_calls_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false",
        "",
    ])


def _write_bundle(path: Path, paths: dict[str, Path]) -> None:
    pd.DataFrame([{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() else "MISSING"} for name, p in paths.items()]).to_csv(path, index=False)


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _slug(value: object) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_") or "match"


def _safety(*, batch_workbench_enabled: bool) -> dict[str, bool]:
    return {"network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "batch_workbench_enabled": batch_workbench_enabled}
