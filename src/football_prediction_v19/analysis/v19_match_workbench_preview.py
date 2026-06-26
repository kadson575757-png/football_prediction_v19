# -*- coding: utf-8 -*-
"""One-command v1.9 match workbench preview from Excel evidence to readiness dashboard."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_completion_validation_preview import (
    V19CompletionValidationConfig,
    V19CompletionValidationRunner,
)
from football_prediction_v19.analysis.v19_machine_readable_workbench_preview import (
    V19MachineReadableWorkbenchConfig,
    V19MachineReadableWorkbenchWriter,
)
from football_prediction_v19.analysis.v19_next_data_to_fill_preview import (
    V19NextDataToFillConfig,
    V19NextDataToFillRenderer,
)
from football_prediction_v19.analysis.v19_promotion_downgrade_simulator_preview import (
    V19PromotionDowngradeSimulator,
    V19PromotionDowngradeSimulatorConfig,
)
from football_prediction_v19.analysis.v19_workbench_dashboard_preview import (
    V19WorkbenchDashboardConfig,
    V19WorkbenchDashboardRenderer,
)

V19_MATCH_WORKBENCH_PREVIEW_READY = "V19_MATCH_WORKBENCH_PREVIEW_READY"
V19_MATCH_WORKBENCH_BLOCKED_PIPELINE_FAILED = "V19_MATCH_WORKBENCH_BLOCKED_PIPELINE_FAILED"
V19_MATCH_WORKBENCH_BLOCKED_UNSAFE_PATH = "V19_MATCH_WORKBENCH_BLOCKED_UNSAFE_PATH"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class V19MatchWorkbenchConfig:
    input_dir: str | Path
    home_team: str
    away_team: str
    competition: str
    season: str
    match_date: str
    manual_evidence_completion: str | Path | None = None
    emit_all: bool = False
    output_dir: str | Path = "outputs/analysis_preview/v19_match_workbench"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19MatchWorkbenchResult:
    v19_match_workbench_status: str
    workbench_preview_enabled: bool
    completion_validation_enabled: bool
    promotion_simulation_enabled: bool
    recommendation_preview_enabled: bool
    production_readiness_gate_enabled: bool
    workbench_output_dir: str
    workbench_dashboard_path: str
    workbench_summary_path: str
    real_match_intake_path: str
    completion_template_path: str
    completion_validation_report_path: str
    completion_validation_json_path: str
    production_readiness_report_path: str
    promotion_downgrade_simulation_path: str
    next_data_to_fill_path: str
    final_decision_card_path: str
    analysis_suite_summary_path: str
    machine_readable_workbench_path: str
    workbench_bundle_index_path: str
    workbench_artifacts_count: int
    excel_files_detected: int
    fields_mapped_count: int
    manual_evidence_completion_status: str
    fields_completed_count: int
    remaining_missing_fields_count: int
    v19_analysis_suite_status: str
    v19_production_readiness_gate_status: str
    evidence_readiness_score: int
    final_decision_class: str
    promotion_allowed: bool
    strong_promotion_allowed: bool
    conflict_score: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19MatchWorkbenchRunner:
    def __init__(self, config: V19MatchWorkbenchConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19MatchWorkbenchResult:
        if _unsafe(self.config.input_dir) or _unsafe(self.config.manual_evidence_completion or ""):
            return self._blocked(V19_MATCH_WORKBENCH_BLOCKED_UNSAFE_PATH)
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)

        from scripts.build_real_match_input_pack_preview import build_real_match_input_pack_preview
        from scripts.build_real_match_intake_from_excel import build_real_match_intake_from_excel
        from scripts.build_v19_manual_evidence_completion_template import build_v19_manual_evidence_completion_template
        from scripts.run_v19_analysis_suite_preview import run_v19_analysis_suite_preview

        intake_path = out / "real_match_intake.csv"
        builder = build_real_match_intake_from_excel(
            input_dir=self.config.input_dir,
            output=intake_path,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            competition=self.config.competition,
            season=self.config.season,
            match_date=self.config.match_date,
            base_dir=self.base,
        )
        if builder.get("real_match_intake_excel_builder_status") != "REAL_MATCH_INTAKE_EXCEL_BUILDER_READY":
            return self._blocked(V19_MATCH_WORKBENCH_BLOCKED_PIPELINE_FAILED)

        template_path = out / "completion_template.csv"
        build_v19_manual_evidence_completion_template(output=template_path, base_dir=self.base)
        _patch_template_context(template_path, self.config)

        input_pack = build_real_match_input_pack_preview(
            real_match_intake_path=intake_path,
            manual_evidence_completion_path=self.config.manual_evidence_completion,
            base_dir=self.base,
        )
        if input_pack.get("real_match_input_pack_status") != "REAL_MATCH_INPUT_PACK_PREVIEW_READY":
            return self._blocked(V19_MATCH_WORKBENCH_BLOCKED_PIPELINE_FAILED)
        completed_intake = self.base / "outputs" / "analysis_preview" / "manual_evidence_completion" / "real_match_intake_completed.csv"

        completion_validation = V19CompletionValidationRunner(
            V19CompletionValidationConfig(
                intake_path=intake_path,
                completion_path=self.config.manual_evidence_completion,
                completed_intake_path=completed_intake,
                fields_completed_count=int(input_pack.get("fields_completed_count", 0) or 0),
                remaining_missing_fields_count=int(input_pack.get("remaining_missing_fields_count", 0) or 0),
                completed_evidence_groups=str(input_pack.get("completed_evidence_groups", "")),
                output_dir=out,
                base_dir=self.base,
            )
        ).run()

        suite = run_v19_analysis_suite_preview(
            real_match_intake_path=intake_path,
            manual_evidence_completion_path=self.config.manual_evidence_completion,
            emit_all=True,
            base_dir=self.base,
        )
        if suite.get("v19_analysis_suite_status") != "V19_ANALYSIS_SUITE_PREVIEW_READY":
            return self._blocked(V19_MATCH_WORKBENCH_BLOCKED_PIPELINE_FAILED)

        readiness = _read_json(suite.get("machine_readable_decision_path", "")).get("production_readiness", {})
        promotion = V19PromotionDowngradeSimulator(
            V19PromotionDowngradeSimulatorConfig(
                final_decision_class=str(suite.get("final_decision_class", "")),
                conflict_score=str(suite.get("conflict_score", "")),
                output_dir=out,
                base_dir=self.base,
            )
        ).run()
        next_data = V19NextDataToFillRenderer(V19NextDataToFillConfig(output_dir=out, base_dir=self.base)).run()

        copied = _copy_suite_artifacts(out, suite)
        artifact_paths = {
            "workbench_dashboard": str((out / "workbench_dashboard.md").resolve()),
            "workbench_summary": str((out / "workbench_summary.md").resolve()),
            "real_match_intake": str(intake_path.resolve()),
            "completion_template": str(template_path.resolve()),
            "completion_validation_report": completion_validation.completion_validation_report_path,
            "completion_validation_json": completion_validation.completion_validation_json_path,
            "production_readiness_report": str((out / "production_readiness_report.md").resolve()),
            "promotion_downgrade_simulation": promotion.promotion_downgrade_simulation_path,
            "next_data_to_fill": next_data.next_data_to_fill_path,
            **copied,
        }
        match = {
            "home_team": self.config.home_team,
            "away_team": self.config.away_team,
            "competition": self.config.competition,
            "season": self.config.season,
            "match_date": self.config.match_date,
        }
        dashboard = V19WorkbenchDashboardRenderer(
            V19WorkbenchDashboardConfig(match=match, production_readiness=readiness, artifact_paths=artifact_paths, output_dir=out, base_dir=self.base)
        ).run()
        artifact_paths["workbench_dashboard"] = dashboard.workbench_dashboard_path

        payload = {
            "match": match,
            "workbench_status": V19_MATCH_WORKBENCH_PREVIEW_READY,
            "input": {
                "excel_input_dir": str(_resolve(self.config.input_dir, self.base)),
                "manual_completion_file": str(_resolve(self.config.manual_evidence_completion, self.base)) if self.config.manual_evidence_completion else "",
                "excel_files_detected": int(builder.get("input_files_detected", 0) or 0),
            },
            "intake": {"real_match_intake_path": str(intake_path.resolve()), "fields_mapped_count": int(builder.get("fields_mapped_count", 0) or 0)},
            "completion_validation": _read_json(completion_validation.completion_validation_json_path),
            "analysis_suite": suite,
            "production_readiness": readiness,
            "promotion_simulation": _read_json(promotion.promotion_downgrade_simulation_json_path),
            "next_data_to_fill": {"path": next_data.next_data_to_fill_path, "critical_groups_count": next_data.critical_groups_count},
            "artifact_paths": artifact_paths,
        }
        machine = V19MachineReadableWorkbenchWriter(V19MachineReadableWorkbenchConfig(payload=payload, output_dir=out, base_dir=self.base)).run()
        artifact_paths["machine_readable_workbench"] = machine.machine_readable_workbench_path
        summary_path = out / "workbench_summary.md"
        bundle_path = out / "workbench_bundle_index.csv"
        _write_summary(summary_path, match, suite, builder, input_pack, artifact_paths)
        artifact_paths["workbench_summary"] = str(summary_path.resolve())
        index = _write_index(bundle_path, artifact_paths)

        return V19MatchWorkbenchResult(
            V19_MATCH_WORKBENCH_PREVIEW_READY,
            True,
            True,
            True,
            True,
            True,
            str(out.resolve()),
            dashboard.workbench_dashboard_path,
            str(summary_path.resolve()),
            str(intake_path.resolve()),
            str(template_path.resolve()),
            completion_validation.completion_validation_report_path,
            completion_validation.completion_validation_json_path,
            str((out / "production_readiness_report.md").resolve()),
            promotion.promotion_downgrade_simulation_path,
            next_data.next_data_to_fill_path,
            artifact_paths.get("final_decision_card", ""),
            artifact_paths.get("analysis_suite_summary", ""),
            machine.machine_readable_workbench_path,
            str(bundle_path.resolve()),
            len(index),
            int(builder.get("input_files_detected", 0) or 0),
            int(builder.get("fields_mapped_count", 0) or 0),
            str(input_pack.get("manual_evidence_completion_status", "")),
            int(input_pack.get("fields_completed_count", 0) or 0),
            int(input_pack.get("remaining_missing_fields_count", 0) or 0),
            str(suite.get("v19_analysis_suite_status", "")),
            str(suite.get("v19_production_readiness_gate_status", "")),
            int(suite.get("evidence_readiness_score", 0) or 0),
            str(suite.get("final_decision_class", "")),
            _bool(suite.get("promotion_allowed", False)),
            _bool(suite.get("strong_promotion_allowed", False)),
            str(suite.get("conflict_score", "")),
            False,
            False,
            False,
            False,
            False,
            V19_MATCH_WORKBENCH_PREVIEW_READY,
        )

    def _blocked(self, status: str) -> V19MatchWorkbenchResult:
        return V19MatchWorkbenchResult(status, False, False, False, False, False, "", "", "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, 0, "", 0, 0, "", "", 0, "", False, False, "", False, False, False, False, False, status)


def _copy_suite_artifacts(out: Path, suite: dict[str, object]) -> dict[str, str]:
    mapping = {
        "production_readiness_report": "production_readiness_report_path",
        "final_decision_card": "final_decision_card_path",
        "analysis_suite_summary": "analysis_suite_summary_path",
        "full_match_analysis": "full_match_analysis_path",
        "decision_report": "decision_report_path",
        "score_tree_detail": "score_tree_detail_path",
        "market_family_matrix": "market_family_matrix_path",
        "no_bet_matrix": "no_bet_matrix_path",
        "evidence_audit": "evidence_audit_path",
        "missing_data_action_plan": "missing_data_action_plan_path",
        "machine_readable_decision": "machine_readable_decision_path",
    }
    copied = {}
    for name, key in mapping.items():
        source = Path(str(suite.get(key, "")))
        if source.exists() and source.is_file():
            target = out / source.name
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)
            copied[name] = str(target.resolve())
    return copied


def _write_summary(path: Path, match: dict[str, object], suite: dict[str, object], builder: dict[str, object], input_pack: dict[str, object], artifacts: dict[str, str]) -> None:
    path.write_text("\n".join([
        "# v1.9 Match Workbench Summary",
        "",
        f"- match: {match['home_team']} vs {match['away_team']} ({match['competition']} {match['season']})",
        f"- excel_files_detected: {builder.get('input_files_detected', 0)}",
        f"- fields_mapped_count: {builder.get('fields_mapped_count', 0)}",
        f"- manual_evidence_completion_status: {input_pack.get('manual_evidence_completion_status', '')}",
        f"- fields_completed_count: {input_pack.get('fields_completed_count', 0)}",
        f"- remaining_missing_fields_count: {input_pack.get('remaining_missing_fields_count', 0)}",
        f"- final_decision_class: {suite.get('final_decision_class', '')}",
        f"- promotion_allowed: {str(suite.get('promotion_allowed', False)).lower()}",
        f"- strong_promotion_allowed: {str(suite.get('strong_promotion_allowed', False)).lower()}",
        "- No production bet. Preview only.",
        "",
        "## Artifact Links",
        *[f"- {name}: {value}" for name, value in artifacts.items()],
        "",
    ]), encoding="utf-8")


def _write_index(path: Path, artifacts: dict[str, str]) -> list[dict[str, object]]:
    rows = [{"artifact_name": name, "path": value, "status": "READY" if Path(value).exists() else "MISSING"} for name, value in artifacts.items()]
    pd.DataFrame(rows).to_csv(path, index=False)
    return rows


def _patch_template_context(path: Path, config: V19MatchWorkbenchConfig) -> None:
    frame = pd.read_csv(path, keep_default_na=False)
    for column, value in {
        "home_team": config.home_team,
        "away_team": config.away_team,
        "competition": config.competition,
        "season": config.season,
        "match_date": config.match_date,
        "cross_provider_match_key": _manual_key(config),
    }.items():
        if column in frame.columns:
            frame.loc[0, column] = value
    frame.to_csv(path, index=False)


def _manual_key(config: V19MatchWorkbenchConfig) -> str:
    return "manual-{competition}-{season}-{home}-{away}-{date}".format(
        competition=_slug(config.competition),
        season=_slug(config.season),
        home=_slug(config.home_team),
        away=_slug(config.away_team),
        date=config.match_date,
    )


def _slug(value: object) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")


def _read_json(path: object) -> dict[str, object]:
    try:
        p = Path(str(path))
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path | None, base: Path) -> Path:
    p = Path(str(path or ""))
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}
