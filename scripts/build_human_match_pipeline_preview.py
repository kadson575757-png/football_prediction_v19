# -*- coding: utf-8 -*-
"""Build Phase 16.5 end-to-end human match pipeline preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_analysis_input_bundle_preview import build_analysis_input_bundle_preview  # noqa: E402
from build_file_based_importer_dry_run_preview import build_file_based_importer_dry_run_preview  # noqa: E402
from build_human_match_analysis_report_preview import build_human_match_analysis_report_preview  # noqa: E402
from build_single_match_analysis_report_preview import build_single_match_analysis_report_preview  # noqa: E402
from build_single_match_context_enrichment_preview import build_single_match_context_enrichment_preview  # noqa: E402
from football_prediction_v19.analysis.human_match_pipeline_preview import (  # noqa: E402
    HUMAN_MATCH_PIPELINE_BETTING_DISABLED_BY_DESIGN,
    HUMAN_MATCH_PIPELINE_BLOCKED_HUMAN_REPORT,
    HUMAN_MATCH_PIPELINE_BLOCKED_INPUT_BUNDLE,
    HUMAN_MATCH_PIPELINE_BLOCKED_SINGLE_MATCH_REPORT,
    HUMAN_MATCH_PIPELINE_BLOCKED_CONTEXT_ENRICHMENT,
    HUMAN_MATCH_PIPELINE_BLOCKED_IMPORTER,
    HUMAN_MATCH_PIPELINE_BLOCKED_UNSAFE_PATH,
    HUMAN_MATCH_PIPELINE_MODEL_DISABLED_BY_DESIGN,
    HUMAN_MATCH_PIPELINE_NETWORK_DISABLED_BY_DESIGN,
    HUMAN_MATCH_PIPELINE_PREVIEW_READY,
    HumanMatchPipelinePreviewConfig,
    HumanMatchPipelinePreviewResult,
    HumanMatchPipelinePreviewRunner,
    build_manifest_frame,
    build_markdown,
    build_step_summary_frame,
)

OUTPUT_DIR = ROOT / "outputs" / "analysis_preview" / "human_match_pipeline"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None)
    parser.add_argument("--match-id", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_human_match_pipeline_preview(*, input_path: str | Path | None = None, match_id: str | None = None, output_dir: str | Path = OUTPUT_DIR, write_preview: bool = False, build_missing: bool = True, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    runner = HumanMatchPipelinePreviewRunner(HumanMatchPipelinePreviewConfig(input_path=input_path, match_id=match_id, output_dir=output_dir, write_preview=write_preview, base_dir=base))
    out_dir = runner.validate_output_dir()
    if out_dir is None:
        return _summary(HUMAN_MATCH_PIPELINE_BLOCKED_UNSAFE_PATH)

    steps: list[dict[str, object]] = []
    importer = build_file_based_importer_dry_run_preview(input_path=input_path, output_dir=base / "outputs" / "importer_preview", write_preview=True, base_dir=base)
    _add_step(steps, "file_based_importer", importer["file_importer_status"], importer.get("normalized_output_path", ""), "FILE_BASED_IMPORTER_DRY_RUN_READY")
    if importer["file_importer_status"] != "FILE_BASED_IMPORTER_DRY_RUN_READY":
        return _blocked(HUMAN_MATCH_PIPELINE_BLOCKED_IMPORTER, steps, out_dir, write_preview)

    bundle = build_analysis_input_bundle_preview(input_path=importer.get("normalized_output_path"), output_dir=base / "outputs" / "analysis_preview" / "input_bundle", write_preview=True, base_dir=base)
    _add_step(steps, "analysis_input_bundle", bundle["analysis_input_bundle_status"], bundle.get("analysis_input_preview_path", ""), "ANALYSIS_INPUT_BUNDLE_PREVIEW_READY")
    if bundle["analysis_input_bundle_status"] != "ANALYSIS_INPUT_BUNDLE_PREVIEW_READY":
        return _blocked(HUMAN_MATCH_PIPELINE_BLOCKED_INPUT_BUNDLE, steps, out_dir, write_preview)

    single = build_single_match_analysis_report_preview(input_path=bundle.get("analysis_input_preview_path"), match_id=match_id, output_dir=base / "outputs" / "analysis_preview" / "single_match_report", write_preview=True, base_dir=base)
    _add_step(steps, "single_match_report", single["single_match_report_status"], single.get("manifest_path", ""), "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY")
    if single["single_match_report_status"] != "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY":
        return _blocked(HUMAN_MATCH_PIPELINE_BLOCKED_SINGLE_MATCH_REPORT, steps, out_dir, write_preview)

    context = build_single_match_context_enrichment_preview(base_report_manifest=single.get("manifest_path"), output_dir=base / "outputs" / "analysis_preview" / "single_match_context", write_preview=True, base_dir=base)
    _add_step(steps, "context_enrichment", context["single_match_context_enrichment_status"], context.get("manifest_path", ""), "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY")
    if context["single_match_context_enrichment_status"] != "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY":
        return _blocked(HUMAN_MATCH_PIPELINE_BLOCKED_CONTEXT_ENRICHMENT, steps, out_dir, write_preview)

    human = build_human_match_analysis_report_preview(context_manifest=context.get("manifest_path"), output_dir=base / "outputs" / "analysis_preview" / "human_match_report", write_preview=True, base_dir=base)
    _add_step(steps, "human_match_report", human["human_match_report_status"], human.get("report_path", ""), "HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY")
    if human["human_match_report_status"] != "HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY":
        return _blocked(HUMAN_MATCH_PIPELINE_BLOCKED_HUMAN_REPORT, steps, out_dir, write_preview)

    result = HumanMatchPipelinePreviewResult(
        pipeline_run_id="human_match_pipeline_preview",
        source_id=str(human.get("source_id", "")),
        provider_match_id=str(human.get("provider_match_id", "")),
        league="",
        season="",
        final_report_path=str(human.get("report_path", "")),
        steps_checked=len(steps),
        steps_ready=sum(1 for row in steps if row["warning"] == ""),
        steps_failed=sum(1 for row in steps if row["warning"] != ""),
        rows_reported=int(human.get("rows_reported", 0)),
        contexts_checked=int(human.get("contexts_checked", 0)),
        contexts_available=int(human.get("contexts_available", 0)),
        contexts_missing_optional=int(human.get("contexts_missing_optional", 0)),
        network_calls_enabled=False,
        prediction_logic_enabled=False,
        betting_logic_enabled=False,
        pipeline_status=HUMAN_MATCH_PIPELINE_PREVIEW_READY,
        recommendation=HUMAN_MATCH_PIPELINE_PREVIEW_READY,
        notes=f"{HUMAN_MATCH_PIPELINE_NETWORK_DISABLED_BY_DESIGN}; {HUMAN_MATCH_PIPELINE_MODEL_DISABLED_BY_DESIGN}; {HUMAN_MATCH_PIPELINE_BETTING_DISABLED_BY_DESIGN}",
    )
    return _write(result, steps, out_dir, write_preview)


def _add_step(rows: list[dict[str, object]], name: str, status: str, path: str, ready_status: str) -> None:
    warning = "" if status == ready_status else f"Expected {ready_status}"
    rows.append({"step_name": name, "step_status": status, "output_path": path, "warning": warning, "recommendation": status, "notes": "preview only"})


def _blocked(status: str, steps: list[dict[str, object]], out_dir: Path, write_preview: bool) -> dict[str, Any]:
    result = HumanMatchPipelinePreviewResult("human_match_pipeline_preview", "", "", "", "", "", len(steps), sum(1 for r in steps if r["warning"] == ""), sum(1 for r in steps if r["warning"] != ""), 0, 0, 0, 0, False, False, False, status, status, status)
    return _write(result, steps, out_dir, write_preview)


def _write(result: HumanMatchPipelinePreviewResult, steps: list[dict[str, object]], out_dir: Path, write_preview: bool) -> dict[str, Any]:
    manifest_path = summary_path = report_path = ""
    step_frame = build_step_summary_frame(steps)
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = (out_dir / "human_match_pipeline_preview_manifest.csv").resolve()
        summary = (out_dir / "human_match_pipeline_step_summary.csv").resolve()
        report = (out_dir / "human_match_pipeline_preview.md").resolve()
        build_manifest_frame(result).to_csv(manifest, index=False)
        step_frame.to_csv(summary, index=False)
        report.write_text(build_markdown(result, step_frame), encoding="utf-8")
        manifest_path, summary_path, report_path = str(manifest), str(summary), str(report)
    return {**_summary(result.pipeline_status), "source_id": result.source_id, "provider_match_id": result.provider_match_id, "rows_reported": result.rows_reported, "steps_checked": result.steps_checked, "steps_ready": result.steps_ready, "steps_failed": result.steps_failed, "contexts_checked": result.contexts_checked, "contexts_available": result.contexts_available, "contexts_missing_optional": result.contexts_missing_optional, "final_report_path": result.final_report_path, "manifest_path": manifest_path, "step_summary_path": summary_path, "pipeline_report_path": report_path, "recommendation": result.recommendation}


def _summary(status: str) -> dict[str, Any]:
    return {"human_match_pipeline_status": status, "source_id": "", "provider_match_id": "", "rows_reported": 0, "steps_checked": 0, "steps_ready": 0, "steps_failed": 0, "contexts_checked": 0, "contexts_available": 0, "contexts_missing_optional": 0, "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "final_report_path": "", "manifest_path": "", "step_summary_path": "", "pipeline_report_path": "", "recommendation": status}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_human_match_pipeline_preview(input_path=args.input, match_id=args.match_id, output_dir=args.output_dir, write_preview=args.write_preview, build_missing=args.build_missing, base_dir=args.base_dir)
    for key in ["human_match_pipeline_status", "source_id", "provider_match_id", "rows_reported", "steps_checked", "steps_ready", "steps_failed", "contexts_checked", "contexts_available", "contexts_missing_optional", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "final_report_path", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if key.endswith('_enabled') else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

