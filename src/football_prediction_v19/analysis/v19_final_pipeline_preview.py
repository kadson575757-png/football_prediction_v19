# -*- coding: utf-8 -*-
"""v1.9 final end-to-end release candidate pipeline preview."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_evidence_fix_plan_preview import write_evidence_fix_plan
from football_prediction_v19.analysis.v19_final_artifact_index_preview import write_final_artifact_index
from football_prediction_v19.analysis.v19_final_machine_readable_preview import write_final_pipeline_json
from football_prediction_v19.analysis.v19_final_pipeline_dashboard_preview import write_final_pipeline_dashboard
from football_prediction_v19.analysis.v19_final_release_readiness_gate_preview import V19_RELEASE_CANDIDATE_READY, run_final_release_readiness_gate
from football_prediction_v19.analysis.v19_final_user_guide_preview import write_final_user_guide
from football_prediction_v19.analysis.v19_match_pack_auto_assembler_preview import assemble_match_pack_manifest
from football_prediction_v19.analysis.v19_raw_evidence_duplicate_detector_preview import detect_raw_evidence_duplicates
from football_prediction_v19.analysis.v19_raw_evidence_file_classifier_preview import classify_raw_evidence_files
from football_prediction_v19.analysis.v19_raw_evidence_grouping_preview import group_raw_evidence_files
from football_prediction_v19.analysis.v19_source_quality_audit_preview import audit_source_quality
from scripts.build_v19_batch_config_from_match_packs_preview import build_v19_batch_config_from_match_packs_preview
from scripts.run_v19_batch_health_gate_preview import run_v19_batch_health_gate_preview
from scripts.run_v19_batch_os_preview import run_v19_batch_os_preview
from scripts.scan_v19_match_packs_preview import scan_v19_match_packs_preview

V19_FINAL_PIPELINE_PREVIEW_READY = "V19_FINAL_PIPELINE_PREVIEW_READY"


@dataclass(frozen=True)
class V19FinalPipelineConfig:
    raw_input_dir: str | Path | None = None
    match_pack_manifest: str | Path | None = None
    batch_config: str | Path | None = None
    single_match_input_dir: str | Path | None = None
    home_team: str = ""
    away_team: str = ""
    competition: str = ""
    season: str = ""
    match_date: str = ""
    output_dir: str | Path = "outputs/analysis_preview/v19_final_pipeline"
    emit_all: bool = False
    base_dir: str | Path = "."


class V19FinalPipelineRunner:
    def __init__(self, config: V19FinalPipelineConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> dict[str, object]:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        input_mode = self._mode()
        raw: dict[str, object] = {}
        scan: dict[str, object] = {}
        health: dict[str, object] = {}
        config_result: dict[str, object] = {}
        batch_config = self._prepare_inputs(input_mode, out, raw, scan, health, config_result)
        batch_os = run_v19_batch_os_preview(batch_config=batch_config, output_dir=out / "batch_os", emit_all=True, preflight_validation_json=health.get("batch_health_gate_result_json_path") or None, base_dir=self.base)
        artifact_paths = {
            "final_user_guide": str((out / "final_user_guide.md").resolve()),
            "final_action_plan": batch_os.get("final_action_plan_path", ""),
            "batch_os_executive_dashboard": batch_os.get("executive_dashboard_path", ""),
            "master_completion_template": batch_os.get("master_completion_template_path", ""),
            "final_pipeline_dashboard": str((out / "final_pipeline_dashboard.md").resolve()),
            "final_release_readiness_report": str((out / "final_reports" / "final_release_readiness_report.md").resolve()),
            "final_pipeline_results_json": str((out / "final_pipeline_results.json").resolve()),
        }
        user_guide = write_final_user_guide(artifact_paths["final_user_guide"])
        artifact_index = write_final_artifact_index(out, artifact_paths)
        artifact_paths.update({"final_artifact_index": artifact_index["final_artifact_index_path"], "final_artifact_index_csv": artifact_index["final_artifact_index_csv_path"]})
        preliminary = self._payload(input_mode, raw, scan, health, batch_os, {}, {}, artifact_paths)
        results_path = write_final_pipeline_json(out / "final_pipeline_results.json", preliminary)
        dashboard = write_final_pipeline_dashboard(artifact_paths["final_pipeline_dashboard"], input_mode=input_mode, release_status="PENDING_RELEASE_READINESS_GATE", batch_os=batch_os, health=health, readiness={}, artifact_paths=artifact_paths)
        artifact_paths["final_pipeline_dashboard"] = dashboard
        readiness = run_final_release_readiness_gate(results_path, out / "final_reports")
        artifact_paths["final_release_readiness_report"] = readiness["final_release_readiness_report_path"]
        dashboard = write_final_pipeline_dashboard(artifact_paths["final_pipeline_dashboard"], input_mode=input_mode, release_status=readiness["final_release_readiness_status"], batch_os=batch_os, health=health, readiness=readiness, artifact_paths=artifact_paths)
        artifact_paths["final_pipeline_dashboard"] = dashboard
        final_payload = self._payload(input_mode, raw, scan, health, batch_os, readiness, {}, artifact_paths)
        results_path = write_final_pipeline_json(out / "final_pipeline_results.json", final_payload)
        bundle = _write_bundle(out / "final_pipeline_bundle_index.csv", artifact_paths)
        result = {
            "v19_final_pipeline_status": V19_FINAL_PIPELINE_PREVIEW_READY,
            "v19_release_candidate_enabled": True,
            "final_pipeline_enabled": True,
            "input_mode": input_mode,
            "batch_os_status": batch_os.get("batch_os_status", ""),
            "final_release_readiness_status": readiness["final_release_readiness_status"],
            "final_dashboard_path": dashboard,
            "final_user_guide_path": user_guide,
            "final_smoke_test_report_path": "",
            "final_pipeline_results_json_path": results_path,
            "final_pipeline_bundle_index_path": bundle,
            "network_calls_enabled": False,
            "prediction_logic_enabled": False,
            "betting_logic_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
            "recommendation": V19_RELEASE_CANDIDATE_READY,
        }
        return result

    def _prepare_inputs(self, input_mode: str, out: Path, raw: dict[str, object], scan: dict[str, object], health: dict[str, object], config_result: dict[str, object]) -> str:
        if input_mode == "RAW_EVIDENCE":
            raw_dir = out / "raw_intake"
            raw.update(classify_raw_evidence_files(_resolve(self.config.raw_input_dir, self.base), raw_dir))
            raw.update(group_raw_evidence_files(raw["raw_file_classification_path"], raw_dir))
            raw.update(audit_source_quality(raw["raw_file_classification_path"], raw_dir))
            raw.update(detect_raw_evidence_duplicates(raw["raw_file_classification_path"], raw_dir))
            raw.update(assemble_match_pack_manifest(_resolve(self.config.raw_input_dir, self.base), raw_dir))
            manifest = raw["auto_match_pack_manifest_path"]
        elif input_mode == "MATCH_PACK_MANIFEST":
            manifest = str(_resolve(self.config.match_pack_manifest, self.base))
        elif input_mode == "SINGLE_MATCH":
            manifest = str(self._single_match_manifest(out))
        else:
            return str(_resolve(self.config.batch_config, self.base))
        scan.update(scan_v19_match_packs_preview(manifest=manifest, output_dir=out / "match_packs", emit_all=True, base_dir=self.base))
        health.update(run_v19_batch_health_gate_preview(validation_json=scan["match_pack_validation_results_json_path"], output_dir=out / "batch_health_gate", emit_all=True, base_dir=self.base))
        config_result.update(build_v19_batch_config_from_match_packs_preview(manifest=manifest, output=out / "batch_config" / "auto_batch_config.csv", emit_all=True, base_dir=self.base))
        raw.update(write_evidence_fix_plan(scan["match_pack_validation_results_csv_path"], out / "raw_intake"))
        return str(config_result["output_path"])

    def _single_match_manifest(self, out: Path) -> Path:
        path = out / "match_packs" / "single_match_manifest.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"match_id": f"{self.config.home_team}_{self.config.away_team}_{self.config.match_date}".lower().replace(" ", "_"), "input_dir": self.config.single_match_input_dir, "home_team": self.config.home_team, "away_team": self.config.away_team, "competition": self.config.competition, "season": self.config.season, "match_date": self.config.match_date, "manual_evidence_completion": "tests/fixtures/manual_evidence_completion/lazio_atalanta_completion.csv", "notes": "single match final pipeline preview", "synthetic_demo_pack": "false", "not_real_match_data": "false", "not_for_prediction": "false"}]).to_csv(path, index=False)
        return path

    def _mode(self) -> str:
        if self.config.raw_input_dir:
            return "RAW_EVIDENCE"
        if self.config.match_pack_manifest:
            return "MATCH_PACK_MANIFEST"
        if self.config.batch_config:
            return "BATCH_CONFIG"
        if self.config.single_match_input_dir:
            return "SINGLE_MATCH"
        raise ValueError("One input mode is required.")

    def _payload(self, input_mode: str, raw: dict[str, object], scan: dict[str, object], health: dict[str, object], batch_os: dict[str, object], readiness: dict[str, object], smoke: dict[str, object], artifacts: dict[str, str]) -> dict[str, object]:
        return {"v19_final_pipeline_status": V19_FINAL_PIPELINE_PREVIEW_READY, "input_mode": input_mode, "release_readiness": readiness, "raw_intake": raw, "match_pack_scan": scan, "batch_health_gate": health, "batch_os": batch_os, "completion_campaign": {}, "completion_rerun": {}, "portfolio_delta": {}, "scenario_lab": {}, "smoke_tests": smoke, "artifact_paths": artifacts, "next_actions": ["Fill missing critical fields", "Rerun completion", "Review portfolio delta"], "safety": {}}


def _write_bundle(path: Path, artifacts: dict[str, str]) -> str:
    pd.DataFrame([{"artifact_name": k, "path": v, "status": "READY" if Path(str(v)).exists() else "MISSING"} for k, v in artifacts.items()]).to_csv(path, index=False)
    return str(path.resolve())


def _resolve(path: str | Path | None, base: Path) -> Path:
    p = Path(str(path))
    return p.resolve() if p.is_absolute() else (base / p).resolve()
