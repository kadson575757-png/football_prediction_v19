# -*- coding: utf-8 -*-
"""End-to-end v1.9 batch operating system preview."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_batch_completion_campaign_preview import V19BatchCompletionCampaignBuilder, V19BatchCompletionCampaignConfig
from football_prediction_v19.analysis.v19_batch_completion_rerun_preview import V19BatchCompletionRerunConfig, V19BatchCompletionRerunRunner
from football_prediction_v19.analysis.v19_batch_os_executive_dashboard_preview import write_executive_dashboard
from football_prediction_v19.analysis.v19_batch_os_machine_readable_preview import write_batch_os_json
from football_prediction_v19.analysis.v19_batch_workbench_preview import V19BatchWorkbenchConfig, V19BatchWorkbenchRunner
from football_prediction_v19.analysis.v19_final_action_plan_preview import write_final_action_plan
from football_prediction_v19.analysis.v19_scenario_batch_lab_preview import V19ScenarioBatchLabConfig, V19ScenarioBatchLabRunner

V19_BATCH_OS_PREVIEW_READY = "V19_BATCH_OS_PREVIEW_READY"


@dataclass(frozen=True)
class V19BatchOSConfig:
    batch_config: str | Path
    output_dir: str | Path = "outputs/analysis_preview/v19_batch_os"
    preflight_validation_json: str | Path | None = None
    emit_all: bool = False
    skip_scenario_batch_lab: bool = False
    skip_empty_rerun: bool = False
    strict: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19BatchOSResult:
    batch_os_status: str
    batch_os_preview_enabled: bool
    batch_workbench_status: str
    batch_completion_campaign_status: str
    batch_completion_rerun_status: str
    portfolio_delta_status: str
    scenario_batch_lab_status: str
    executive_dashboard_enabled: bool
    batch_workbench_enabled: bool
    batch_completion_campaign_enabled: bool
    batch_completion_rerun_enabled: bool
    portfolio_delta_enabled: bool
    scenario_batch_lab_enabled: bool
    output_dir: str
    executive_dashboard_path: str
    batch_os_summary_path: str
    batch_dashboard_path: str
    campaign_dashboard_path: str
    master_completion_template_path: str
    portfolio_delta_dashboard_path: str
    candidate_change_report_path: str
    no_bet_change_report_path: str
    missing_data_progress_report_path: str
    readiness_delta_ranking_path: str
    scenario_batch_lab_dashboard_path: str
    final_action_plan_path: str
    batch_os_results_json_path: str
    batch_os_bundle_index_path: str
    matches_total: int
    matches_succeeded: int
    matches_failed: int
    fillable_fields_total: int
    critical_fields_total: int
    filled_values_count: int
    candidate_count_delta: int
    average_readiness_delta: float
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19BatchOSRunner:
    def __init__(self, config: V19BatchOSConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19BatchOSResult:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        preflight = _read_json(_resolve(self.config.preflight_validation_json, self.base)) if self.config.preflight_validation_json else {}
        if self.config.strict and preflight.get("batch_health_status") == "INVALID":
            raise ValueError("Batch OS preflight blocked: batch_health_status=INVALID")
        workbench = V19BatchWorkbenchRunner(V19BatchWorkbenchConfig(self.config.batch_config, output_dir=out / "batch_workbench", emit_all=True, base_dir=self.base)).run()
        campaign = V19BatchCompletionCampaignBuilder(V19BatchCompletionCampaignConfig(workbench.batch_results_json_path, output_dir=out / "completion_campaign", emit_all=True, base_dir=self.base)).run()
        rerun = V19BatchCompletionRerunRunner(V19BatchCompletionRerunConfig(workbench.batch_results_json_path, campaign.master_completion_template_path, self.config.batch_config, output_dir=out / "completion_rerun", emit_all=True, base_dir=self.base)).run() if not self.config.skip_empty_rerun else None
        scenario = V19ScenarioBatchLabRunner(V19ScenarioBatchLabConfig(workbench.batch_results_json_path, output_dir=out / "scenario_batch_lab", emit_all=True, base_dir=self.base)).run() if not self.config.skip_scenario_batch_lab else None
        paths = {
            "executive_dashboard": out / "executive_dashboard.md",
            "batch_os_summary": out / "batch_os_summary.md",
            "batch_dashboard": out / "batch_dashboard.md",
            "campaign_dashboard": out / "campaign_dashboard.md",
            "master_completion_template": out / "master_completion_template.csv",
            "portfolio_delta_dashboard": out / "portfolio_delta_dashboard.md",
            "candidate_change_report": out / "candidate_change_report.md",
            "no_bet_change_report": out / "no_bet_change_report.md",
            "missing_data_progress_report": out / "missing_data_progress_report.md",
            "readiness_delta_ranking": out / "readiness_delta_ranking.csv",
            "scenario_batch_lab_dashboard": out / "scenario_batch_lab_dashboard.md",
            "final_action_plan": out / "final_action_plan.md",
            "batch_os_results": out / "batch_os_results.json",
            "bundle": out / "batch_os_bundle_index.csv",
        }
        _copy(workbench.batch_dashboard_path, paths["batch_dashboard"])
        _copy(campaign.campaign_dashboard_path, paths["campaign_dashboard"])
        _copy(campaign.master_completion_template_path, paths["master_completion_template"])
        if rerun:
            _copy(rerun.portfolio_delta_dashboard_path, paths["portfolio_delta_dashboard"])
            _copy(rerun.candidate_change_report_path, paths["candidate_change_report"])
            _copy(rerun.no_bet_change_report_path, paths["no_bet_change_report"])
            _copy(rerun.missing_data_progress_report_path, paths["missing_data_progress_report"])
            _copy(rerun.readiness_delta_ranking_path, paths["readiness_delta_ranking"])
        if scenario:
            _copy(scenario.scenario_batch_lab_dashboard_path, paths["scenario_batch_lab_dashboard"])
        final_action = write_final_action_plan(paths["final_action_plan"], master_template_path=str(paths["master_completion_template"]), batch_config=str(self.config.batch_config))
        exec_path = write_executive_dashboard(paths["executive_dashboard"], matches_total=workbench.matches_total, matches_succeeded=workbench.matches_succeeded, matches_failed=workbench.matches_failed, fillable_fields_total=campaign.fillable_fields_total, critical_fields_total=campaign.critical_fields_total, candidate_count_delta=rerun.candidate_count_delta if rerun else 0, average_readiness_delta=rerun.average_readiness_delta if rerun else 0, scenario_status=scenario.scenario_batch_lab_status if scenario else "SKIPPED")
        if preflight.get("batch_health_status") == "PARTIAL_READY":
            Path(exec_path).write_text(Path(exec_path).read_text(encoding="utf-8") + "\n## Preflight Warning\n\n- batch_health_status: PARTIAL_READY\n- Batch OS continued for runnable packs only.\n", encoding="utf-8")
        paths["batch_os_summary"].write_text(_summary(workbench, campaign, rerun, scenario), encoding="utf-8")
        payload = {
            "batch_os_status": V19_BATCH_OS_PREVIEW_READY,
            "batch_config": str(_resolve(self.config.batch_config, self.base)),
            "batch_workbench": workbench.__dict__,
            "completion_campaign": campaign.__dict__,
            "completion_rerun": rerun.__dict__ if rerun else {},
            "portfolio_delta": _read_json(rerun.portfolio_delta_json_path) if rerun else {},
            "scenario_batch_lab": scenario.__dict__ if scenario else {},
            "preflight": preflight,
            "executive_dashboard": {"path": exec_path},
            "final_action_plan": {"path": final_action},
            "artifact_paths": {name: str(path.resolve()) for name, path in paths.items()},
        }
        write_batch_os_json(paths["batch_os_results"], payload)
        _write_bundle(paths["bundle"], paths)
        return V19BatchOSResult(
            V19_BATCH_OS_PREVIEW_READY, True, workbench.batch_workbench_status, campaign.batch_completion_campaign_status, rerun.batch_completion_rerun_status if rerun else "SKIPPED", rerun.portfolio_delta_status if rerun else "SKIPPED", scenario.scenario_batch_lab_status if scenario else "SKIPPED", True, True, True, bool(rerun), bool(rerun), bool(scenario), str(out.resolve()), exec_path, str(paths["batch_os_summary"].resolve()), str(paths["batch_dashboard"].resolve()), str(paths["campaign_dashboard"].resolve()), str(paths["master_completion_template"].resolve()), str(paths["portfolio_delta_dashboard"].resolve()), str(paths["candidate_change_report"].resolve()), str(paths["no_bet_change_report"].resolve()), str(paths["missing_data_progress_report"].resolve()), str(paths["readiness_delta_ranking"].resolve()), str(paths["scenario_batch_lab_dashboard"].resolve()), final_action, str(paths["batch_os_results"].resolve()), str(paths["bundle"].resolve()), workbench.matches_total, workbench.matches_succeeded, workbench.matches_failed, campaign.fillable_fields_total, campaign.critical_fields_total, rerun.filled_values_count if rerun else 0, rerun.candidate_count_delta if rerun else 0, rerun.average_readiness_delta if rerun else 0, False, False, False, False, False, V19_BATCH_OS_PREVIEW_READY)


def _summary(workbench: object, campaign: object, rerun: object | None, scenario: object | None) -> str:
    return "\n".join(["# v1.9 Batch OS Summary", "", f"- matches_total: {workbench.matches_total}", f"- fillable_fields_total: {campaign.fillable_fields_total}", f"- critical_fields_total: {campaign.critical_fields_total}", f"- filled_values_count: {rerun.filled_values_count if rerun else 0}", f"- scenario_batch_lab_status: {scenario.scenario_batch_lab_status if scenario else 'SKIPPED'}", ""])


def _copy(source: str | Path, target: Path) -> None:
    if not str(source).strip():
        return
    src = Path(str(source))
    if src.exists() and src.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)


def _write_bundle(path: Path, paths: dict[str, Path]) -> None:
    rows = []
    for name, artifact_path in paths.items():
        status = "READY" if artifact_path.exists() or artifact_path == path else "MISSING"
        rows.append({"artifact_name": name, "path": str(artifact_path.resolve()), "status": status})
    pd.DataFrame(rows).to_csv(path, index=False)


def _read_json(path: str | Path) -> dict[str, object]:
    try:
        return json.loads(Path(str(path)).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
