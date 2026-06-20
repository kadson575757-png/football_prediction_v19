# -*- coding: utf-8 -*-
"""Audit Phase 16.6 human analysis preview layer closure."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_human_match_pipeline_preview import build_human_match_pipeline_preview  # noqa: E402
from build_importer_adapter_interface_preview import build_importer_adapter_interface_preview  # noqa: E402
from build_importer_schema_contracts_preview import build_importer_schema_contracts_preview  # noqa: E402
from build_importer_source_registry_preview import build_importer_source_registry_preview  # noqa: E402

HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE = "HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE"
HUMAN_ANALYSIS_PREVIEW_LAYER_PARTIAL_READY = "HUMAN_ANALYSIS_PREVIEW_LAYER_PARTIAL_READY"
HUMAN_ANALYSIS_PREVIEW_LAYER_BLOCKED = "HUMAN_ANALYSIS_PREVIEW_LAYER_BLOCKED"
HUMAN_ANALYSIS_PREVIEW_LAYER_MODEL_DISABLED_BY_DESIGN = "HUMAN_ANALYSIS_PREVIEW_LAYER_MODEL_DISABLED_BY_DESIGN"
HUMAN_ANALYSIS_PREVIEW_LAYER_BETTING_DISABLED_BY_DESIGN = "HUMAN_ANALYSIS_PREVIEW_LAYER_BETTING_DISABLED_BY_DESIGN"
MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN = "MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN"
READY_RECOMMENDATION = "HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE_READY_FOR_HUMAN_REVIEW"

OUTPUT_CSV = "human_analysis_preview_layer_closure_summary.csv"
OUTPUT_MD = "human_analysis_preview_layer_closure_summary.md"

CLOSURE_COLUMNS = [
    "closure_status", "pipeline_status", "human_report_status",
    "context_enrichment_status", "single_match_report_status",
    "input_bundle_status", "file_importer_status", "adapter_interface_status",
    "schema_contract_status", "source_registry_status", "rows_reported",
    "steps_checked", "steps_ready", "steps_failed", "contexts_checked",
    "contexts_available", "contexts_missing_optional", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled",
    "model_integration_status", "recommendation", "notes",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _read_first(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path, low_memory=False)
    if frame.empty:
        return {}
    return frame.iloc[0].to_dict()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def build_closure_summary(*, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    pipeline = build_human_match_pipeline_preview(output_dir=base / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=base)
    importer_dir = base / "outputs" / "importer_preview"
    registry = build_importer_source_registry_preview(output_dir=importer_dir, write_preview=True, base_dir=base)
    schema = build_importer_schema_contracts_preview(registry=registry.get("registry_output_path") or "", output_dir=importer_dir, write_preview=True, base_dir=base)
    adapter = build_importer_adapter_interface_preview(
        registry=registry.get("registry_output_path") or "",
        contracts=schema.get("contracts_output_path") or "",
        output_dir=importer_dir,
        write_preview=True,
        base_dir=base,
    )

    human = _read_first(base / "outputs" / "analysis_preview" / "human_match_report" / "human_match_analysis_report_manifest.csv")
    context = _read_first(base / "outputs" / "analysis_preview" / "single_match_context" / "single_match_context_enrichment_manifest.csv")
    single = _read_first(base / "outputs" / "analysis_preview" / "single_match_report" / "single_match_analysis_report_manifest.csv")
    bundle = _read_first(base / "outputs" / "analysis_preview" / "input_bundle" / "analysis_input_bundle_manifest.csv")
    file_importer = _read_first(base / "outputs" / "importer_preview" / "file_based_importer_dry_run_preview.csv")

    pipeline_status = str(pipeline.get("human_match_pipeline_status", ""))
    human_status = str(human.get("human_report_status", ""))
    context_status = str(context.get("enrichment_status", ""))
    single_status = str(single.get("report_status", ""))
    bundle_status = str(bundle.get("bundle_status", ""))
    file_status = str(file_importer.get("dry_run_status", ""))
    adapter_status = str(adapter.get("importer_adapter_interface_status", ""))
    schema_status = "IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY" if (base / "outputs" / "importer_preview" / "importer_schema_contracts_preview.csv").exists() else ""
    registry_status = "IMPORTER_SOURCE_REGISTRY_PREVIEW_READY" if (base / "outputs" / "importer_preview" / "importer_source_registry_preview.csv").exists() else ""

    ready = {
        pipeline_status == "HUMAN_MATCH_PIPELINE_PREVIEW_READY",
        human_status == "HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY",
        context_status == "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY",
        single_status == "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY",
        bundle_status == "ANALYSIS_INPUT_BUNDLE_PREVIEW_READY",
        file_status == "FILE_BASED_IMPORTER_DRY_RUN_READY",
        adapter_status == "IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY",
        schema_status == "IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY",
        registry_status == "IMPORTER_SOURCE_REGISTRY_PREVIEW_READY",
        not _as_bool(pipeline.get("network_calls_enabled", False)),
        not _as_bool(pipeline.get("prediction_logic_enabled", False)),
        not _as_bool(pipeline.get("betting_logic_enabled", False)),
    }
    closure_status = HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE if all(ready) else HUMAN_ANALYSIS_PREVIEW_LAYER_BLOCKED
    recommendation = READY_RECOMMENDATION if closure_status == HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE else HUMAN_ANALYSIS_PREVIEW_LAYER_BLOCKED

    return {
        "closure_status": closure_status,
        "pipeline_status": pipeline_status,
        "human_report_status": human_status,
        "context_enrichment_status": context_status,
        "single_match_report_status": single_status,
        "input_bundle_status": bundle_status,
        "file_importer_status": file_status,
        "adapter_interface_status": adapter_status,
        "schema_contract_status": schema_status,
        "source_registry_status": registry_status,
        "rows_reported": int(pipeline.get("rows_reported", 0)),
        "steps_checked": int(pipeline.get("steps_checked", 0)),
        "steps_ready": int(pipeline.get("steps_ready", 0)),
        "steps_failed": int(pipeline.get("steps_failed", 0)),
        "contexts_checked": int(pipeline.get("contexts_checked", 0)),
        "contexts_available": int(pipeline.get("contexts_available", 0)),
        "contexts_missing_optional": int(pipeline.get("contexts_missing_optional", 0)),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "model_integration_status": MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN,
        "recommendation": recommendation,
        "notes": f"{HUMAN_ANALYSIS_PREVIEW_LAYER_MODEL_DISABLED_BY_DESIGN}; {HUMAN_ANALYSIS_PREVIEW_LAYER_BETTING_DISABLED_BY_DESIGN}; optional missing context is summarized and not inferred.",
    }


def build_markdown(row: dict[str, Any]) -> str:
    return "\n".join([
        "# Phase 16.6 Closure Header",
        "",
        "## Human Analysis Preview Layer Status",
        f"- closure_status: {row['closure_status']}",
        "- ready for human review workflows: yes" if row["closure_status"] == HUMAN_ANALYSIS_PREVIEW_LAYER_COMPLETE else "- ready for human review workflows: no",
        "",
        "## Pipeline Status",
        f"- {row['pipeline_status']}",
        "",
        "## Human Report Status",
        f"- {row['human_report_status']}",
        "",
        "## Context Enrichment Status",
        f"- {row['context_enrichment_status']}",
        "",
        "## Single Match Report Status",
        f"- {row['single_match_report_status']}",
        "",
        "## Analysis Input Bundle Status",
        f"- {row['input_bundle_status']}",
        "",
        "## File-Based Importer Status",
        f"- {row['file_importer_status']}",
        "",
        "## Importer Contracts Status",
        f"- adapter: {row['adapter_interface_status']}",
        f"- schema: {row['schema_contract_status']}",
        f"- registry: {row['source_registry_status']}",
        "",
        "## Safety Gates",
        "- network_calls_enabled=false",
        "- prediction_logic_enabled=false",
        "- betting_logic_enabled=false",
        "",
        "## Missing Optional Context Summary",
        f"- contexts_missing_optional: {row['contexts_missing_optional']}",
        "- optional missing context is summarized and not inferred.",
        "",
        "## Model / Prediction / Betting Integration Status",
        f"- {row['model_integration_status']}",
        "- no model predictions are run",
        "- no betting/staking recommendations are generated",
        "",
        "## Closure Recommendation",
        str(row["recommendation"]),
        "",
    ])


def run(*, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    row = build_closure_summary(base_dir=base_dir)
    table = pd.DataFrame([row], columns=CLOSURE_COLUMNS)
    markdown = build_markdown(row)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, str(row["recommendation"])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(output_dir=args.output_dir, base_dir=args.base_dir)
    row = table.iloc[0]
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(f"human_analysis_preview_layer_status={row['closure_status']}")
    print(f"pipeline_status={row['pipeline_status']}")
    print(f"human_report_status={row['human_report_status']}")
    print(f"rows_reported={row['rows_reported']}")
    print(f"steps_failed={row['steps_failed']}")
    print(f"network_calls_enabled={str(row['network_calls_enabled']).lower()}")
    print(f"prediction_logic_enabled={str(row['prediction_logic_enabled']).lower()}")
    print(f"betting_logic_enabled={str(row['betting_logic_enabled']).lower()}")
    print(f"recommendation={rec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
