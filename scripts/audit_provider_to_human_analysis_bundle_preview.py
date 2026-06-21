# -*- coding: utf-8 -*-
"""Audit Phase 18.3 provider-to-human analysis bundle preview."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from build_provider_to_human_analysis_bundle_preview import build_provider_to_human_analysis_bundle_preview
from football_prediction_v19.analysis.provider_to_human_analysis_bundle_preview import MANIFEST_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PARTIAL_READY = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PARTIAL_READY"
BUILD_PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW = "BUILD_PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW"
FIX_PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW = "FIX_PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW"
OUTPUT_CSV = "provider_to_human_analysis_bundle_preview_summary.csv"
OUTPUT_MD = "provider_to_human_analysis_bundle_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _safe_preview_path(path_text: str, base: Path) -> bool:
    if not str(path_text).strip():
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    allowed = (base / "outputs" / "analysis_preview").resolve()
    text = str(resolved).replace("\\", "/").lower()
    return (resolved == allowed or allowed in resolved.parents) and not any(token in text for token in PROTECTED)


def run(*, manifest: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    manifest_path = Path(manifest) if manifest else base / "outputs" / "analysis_preview" / "provider_to_human_bundle" / "provider_to_human_analysis_bundle_manifest.csv"
    if not manifest_path.exists():
        build_provider_to_human_analysis_bundle_preview(base_dir=base, output_dir=base / "outputs" / "analysis_preview" / "provider_to_human_bundle")
    errors: list[str] = []
    if not manifest_path.exists():
        table = pd.DataFrame()
        rec = BUILD_PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW
    else:
        manifest_frame = pd.read_csv(manifest_path, low_memory=False)
        missing = sorted(set(MANIFEST_COLUMNS) - set(manifest_frame.columns))
        row = manifest_frame.iloc[0].to_dict() if not manifest_frame.empty else {}
        checks = {
            "required_columns": not missing,
            "bundle_ready": row.get("bundle_status") in {PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY, PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PARTIAL_READY},
            "provider_pull_ready": row.get("provider_pull_status") == "UNDERSTAT_PROVIDER_PULL_PREVIEW_READY",
            "match_finder_ready": row.get("match_finder_status") == "PROVIDER_MATCH_FINDER_PREVIEW_READY",
            "manual_bridge_ready": row.get("manual_input_bridge_status") == "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY",
            "validation_ready": row.get("validation_status") == "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY",
            "pipeline_ready": row.get("human_match_pipeline_status") == "HUMAN_MATCH_PIPELINE_PREVIEW_READY",
            "rows_reported_one": int(row.get("rows_reported", 0) or 0) == 1,
            "steps_failed_zero": int(row.get("steps_failed", 0) or 0) == 0,
            "network_disabled": not _as_bool(row.get("network_calls_enabled", True)),
            "prediction_disabled": not _as_bool(row.get("prediction_logic_enabled", True)),
            "betting_disabled": not _as_bool(row.get("betting_logic_enabled", True)),
            "final_report_safe": _safe_preview_path(str(row.get("final_report_path", "")), base),
        }
        errors = [key for key, ok in checks.items() if not ok]
        rec = PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY if not errors else FIX_PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW
        table = pd.DataFrame([{**checks, "manifest_path": str(manifest_path), "preview_valid": not errors, "blocking_reasons": " | ".join(errors), "recommendation": rec}])
    markdown = "\n".join([
        "# Phase 18.3 Provider-to-Human Analysis Bundle Preview Audit",
        "",
        f"- preview_valid: {str(rec == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY).lower()}",
        f"- recommendation: {rec}",
        "- no model/prediction/market/betting/staking logic is invoked",
        "",
    ])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _table, _markdown, rec = run(manifest=args.manifest, output_dir=args.output_dir, base_dir=args.base_dir)
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
