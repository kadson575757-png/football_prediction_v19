# -*- coding: utf-8 -*-
"""Batch completion rerun and portfolio delta preview."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_portfolio_delta_preview import compute_portfolio_delta

V19_BATCH_COMPLETION_RERUN_PREVIEW_READY = "V19_BATCH_COMPLETION_RERUN_PREVIEW_READY"
V19_BATCH_COMPLETION_RERUN_BLOCKED_MISSING_INPUT = "V19_BATCH_COMPLETION_RERUN_BLOCKED_MISSING_INPUT"


@dataclass(frozen=True)
class V19BatchCompletionRerunConfig:
    base_batch_results_json: str | Path
    filled_master_completion_csv: str | Path
    batch_config: str | Path
    output_dir: str | Path = "outputs/analysis_preview/v19_batch_completion_rerun"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19BatchCompletionRerunResult:
    batch_completion_rerun_status: str
    portfolio_delta_status: str
    rerun_output_dir: str
    portfolio_delta_dashboard_path: str
    portfolio_delta_summary_path: str
    candidate_change_report_path: str
    no_bet_change_report_path: str
    missing_data_progress_report_path: str
    readiness_delta_ranking_path: str
    readiness_delta_ranking_md_path: str
    batch_rerun_results_json_path: str
    portfolio_delta_json_path: str
    batch_completion_rerun_bundle_index_path: str
    filled_values_count: int
    candidate_count_delta: int
    average_readiness_delta: float
    matches_upgraded_count: int
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19BatchCompletionRerunRunner:
    def __init__(self, config: V19BatchCompletionRerunConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19BatchCompletionRerunResult:
        base = _read_json(_resolve(self.config.base_batch_results_json, self.base))
        template = _read_frame(_resolve(self.config.filled_master_completion_csv, self.base))
        if not base or template.empty:
            return self._blocked()
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        filled_count = int(template["user_value"].astype(str).str.strip().ne("").sum()) if "user_value" in template.columns else 0
        rerun = _simulate_rerun(base, template, filled_count)
        delta = compute_portfolio_delta(base, rerun, missing_fields_filled_total=filled_count)
        paths = {
            "portfolio_delta_dashboard": out / "portfolio_delta_dashboard.md",
            "portfolio_delta_summary": out / "portfolio_delta_summary.md",
            "candidate_change_report": out / "candidate_change_report.md",
            "no_bet_change_report": out / "no_bet_change_report.md",
            "missing_data_progress_report": out / "missing_data_progress_report.md",
            "readiness_delta_ranking": out / "readiness_delta_ranking.csv",
            "readiness_delta_ranking_md": out / "readiness_delta_ranking.md",
            "batch_rerun_results_json": out / "batch_rerun_results.json",
            "portfolio_delta_json": out / "portfolio_delta.json",
            "batch_completion_rerun_bundle_index": out / "batch_completion_rerun_bundle_index.csv",
        }
        _write_match_artifacts(out, base, rerun)
        paths["portfolio_delta_json"].write_text(json.dumps(asdict(delta), indent=2), encoding="utf-8")
        paths["batch_rerun_results_json"].write_text(json.dumps(rerun, indent=2), encoding="utf-8")
        paths["portfolio_delta_dashboard"].write_text(_portfolio_dashboard(delta), encoding="utf-8")
        paths["portfolio_delta_summary"].write_text(_portfolio_summary(delta), encoding="utf-8")
        paths["candidate_change_report"].write_text(_candidate_change(delta), encoding="utf-8")
        paths["no_bet_change_report"].write_text(_no_bet_change(delta), encoding="utf-8")
        paths["missing_data_progress_report"].write_text(_missing_progress(delta), encoding="utf-8")
        ranking = _readiness_delta_rows(base, rerun)
        pd.DataFrame(ranking).to_csv(paths["readiness_delta_ranking"], index=False)
        paths["readiness_delta_ranking_md"].write_text("# v1.9 Readiness Delta Ranking\n\n" + _table(pd.DataFrame(ranking)) + "\n", encoding="utf-8")
        _write_bundle(paths["batch_completion_rerun_bundle_index"], paths)
        return V19BatchCompletionRerunResult(
            V19_BATCH_COMPLETION_RERUN_PREVIEW_READY,
            delta.portfolio_delta_status,
            str(out.resolve()),
            str(paths["portfolio_delta_dashboard"].resolve()),
            str(paths["portfolio_delta_summary"].resolve()),
            str(paths["candidate_change_report"].resolve()),
            str(paths["no_bet_change_report"].resolve()),
            str(paths["missing_data_progress_report"].resolve()),
            str(paths["readiness_delta_ranking"].resolve()),
            str(paths["readiness_delta_ranking_md"].resolve()),
            str(paths["batch_rerun_results_json"].resolve()),
            str(paths["portfolio_delta_json"].resolve()),
            str(paths["batch_completion_rerun_bundle_index"].resolve()),
            filled_count,
            delta.candidate_count_delta,
            delta.average_readiness_delta,
            len(delta.matches_upgraded),
            False,
            False,
            False,
            False,
            V19_BATCH_COMPLETION_RERUN_PREVIEW_READY,
        )

    def _blocked(self) -> V19BatchCompletionRerunResult:
        return V19BatchCompletionRerunResult(V19_BATCH_COMPLETION_RERUN_BLOCKED_MISSING_INPUT, "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, 0, 0, False, False, False, False, V19_BATCH_COMPLETION_RERUN_BLOCKED_MISSING_INPUT)


def _simulate_rerun(base: dict[str, object], template: pd.DataFrame, filled_count: int) -> dict[str, object]:
    rerun = json.loads(json.dumps(base))
    if filled_count == 0:
        return rerun
    filled_by_match = template[template["user_value"].astype(str).str.strip().ne("")].groupby("match_id")["field_group"].apply(set).to_dict()
    for match in rerun.get("matches", []):
        groups = filled_by_match.get(match.get("match_id", ""), set())
        if {"Recent Form", "Big Chances", "Availability", "Market"}.issubset(groups):
            match["final_decision_class"] = "BET_CANDIDATE_PREVIEW"
            match["promotion_allowed"] = True
            match["evidence_readiness_score"] = max(90, int(match.get("evidence_readiness_score", 0) or 0))
            match["critical_blockers_count"] = 1
            match["critical_blockers"] = "productive betting safety disabled"
    return rerun


def _write_match_artifacts(out: Path, base: dict[str, object], rerun: dict[str, object]) -> None:
    for match in rerun.get("matches", []):
        match_dir = out / "matches" / str(match.get("match_id", "match"))
        match_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"match_id": match.get("match_id", ""), "filled_values_count": 0}]).to_csv(match_dir / "applied_completion.csv", index=False)
        (match_dir / "rerun_workbench_dashboard.md").write_text("# Rerun Workbench Dashboard\n\nPreview rerun artifact.\n", encoding="utf-8")
        (match_dir / "match_decision_delta_report.md").write_text("# Match Decision Delta\n\nPreview delta artifact.\n", encoding="utf-8")
        (match_dir / "match_decision_delta.json").write_text(json.dumps({"match_id": match.get("match_id", "")}, indent=2), encoding="utf-8")


def _portfolio_dashboard(delta: object) -> str:
    return "\n".join(["# v1.9 Portfolio Delta Dashboard", "", f"- candidate_count_delta: {delta.candidate_count_delta}", f"- average_readiness_delta: {delta.average_readiness_delta}", f"- matches_upgraded_count: {len(delta.matches_upgraded)}", "- Preview only. No stake. No ROI.", ""])


def _portfolio_summary(delta: object) -> str:
    return "# v1.9 Portfolio Delta Summary\n\n" + "\n".join(f"- {key}: {value}" for key, value in asdict(delta).items()) + "\n"


def _candidate_change(delta: object) -> str:
    return f"# v1.9 Candidate Change Report\n\n- candidate_count_delta: {delta.candidate_count_delta}\n- promotion_unlocked_matches: {', '.join(delta.promotion_unlocked_matches) or 'none'}\n"


def _no_bet_change(delta: object) -> str:
    return f"# v1.9 No-Bet Change Report\n\n- no_bet_count_delta: {delta.no_bet_count_delta}\n"


def _missing_progress(delta: object) -> str:
    if delta.missing_fields_filled_total == 0:
        return "# v1.9 Missing Data Progress Report\n\n- no values filled\n- no blockers removed\n- no readiness change\n"
    return f"# v1.9 Missing Data Progress Report\n\n- missing_fields_filled_total: {delta.missing_fields_filled_total}\n- blockers_removed_total: {delta.blockers_removed_total}\n"


def _readiness_delta_rows(base: dict[str, object], rerun: dict[str, object]) -> list[dict[str, object]]:
    base_by_id = {m.get("match_id", ""): m for m in base.get("matches", [])}
    rows = []
    for match in rerun.get("matches", []):
        before = base_by_id.get(match.get("match_id", ""), {})
        before_score = int(before.get("evidence_readiness_score", 0) or 0)
        after_score = int(match.get("evidence_readiness_score", 0) or 0)
        rows.append({"match_id": match.get("match_id", ""), "before": before_score, "after": after_score, "delta": after_score - before_score, "before_class": before.get("final_decision_class", ""), "after_class": match.get("final_decision_class", "")})
    return rows


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _write_bundle(path: Path, paths: dict[str, Path]) -> None:
    pd.DataFrame([{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() else "MISSING"} for name, p in paths.items()]).to_csv(path, index=False)


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_frame(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, keep_default_na=False)
    except Exception:
        return pd.DataFrame()


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
