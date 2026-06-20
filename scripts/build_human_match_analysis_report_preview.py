# -*- coding: utf-8 -*-
"""Build Phase 16.4 human match analysis report preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_single_match_context_enrichment_preview import build_single_match_context_enrichment_preview  # noqa: E402
from football_prediction_v19.analysis.human_match_analysis_report import (  # noqa: E402
    HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH,
    HumanMatchAnalysisReportBuilder,
    HumanMatchAnalysisReportConfig,
    build_manifest_frame,
)

OUTPUT_DIR = ROOT / "outputs" / "analysis_preview" / "human_match_report"
MANIFEST_CSV = "human_match_analysis_report_manifest.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-manifest", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--build-missing-context", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_preview" / "human_match_report").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _default_context(base: Path) -> Path:
    return base / "outputs" / "analysis_preview" / "single_match_context" / "single_match_context_enrichment_manifest.csv"


def _ensure_context(path: Path | None, base: Path, build_missing: bool) -> Path | None:
    if path is not None:
        return path
    default = _default_context(base)
    if default.exists() or not build_missing:
        return default
    build_single_match_context_enrichment_preview(output_dir=base / "outputs" / "analysis_preview" / "single_match_context", write_preview=True, base_dir=base)
    return default


def build_human_match_analysis_report_preview(*, context_manifest: str | Path | None = None, output_dir: str | Path = OUTPUT_DIR, write_preview: bool = False, build_missing_context: bool = True, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    out_dir = _safe_output_dir(output_dir, base)
    if out_dir is None:
        return _summary(HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH)
    manifest = Path(context_manifest) if context_manifest is not None else None
    if manifest is not None and not manifest.is_absolute():
        manifest = base / manifest
    resolved = _ensure_context(manifest, base, build_missing_context)
    builder = HumanMatchAnalysisReportBuilder(HumanMatchAnalysisReportConfig(context_manifest_path=resolved, output_dir=out_dir, write_preview=write_preview, base_dir=base))
    result, _summary_frame, _markdown = builder.build()
    manifest_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = (out_dir / MANIFEST_CSV).resolve()
        build_manifest_frame(result).to_csv(manifest_file, index=False)
        manifest_path = str(manifest_file)
    return {
        "human_match_report_status": result.human_report_status,
        "source_id": result.source_id,
        "provider_match_id": result.provider_match_id,
        "rows_reported": result.rows_reported,
        "contexts_checked": result.contexts_checked,
        "contexts_available": result.contexts_available,
        "contexts_missing_optional": result.contexts_missing_optional,
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "report_path": result.output_report_path,
        "summary_path": result.output_summary_path,
        "manifest_path": manifest_path,
        "recommendation": result.recommendation,
    }


def _summary(status: str) -> dict[str, Any]:
    return {"human_match_report_status": status, "source_id": "", "provider_match_id": "", "rows_reported": 0, "contexts_checked": 0, "contexts_available": 0, "contexts_missing_optional": 0, "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "report_path": "", "summary_path": "", "manifest_path": "", "recommendation": status}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_human_match_analysis_report_preview(context_manifest=args.context_manifest, output_dir=args.output_dir, write_preview=args.write_preview, build_missing_context=args.build_missing_context, base_dir=args.base_dir)
    for key in ["human_match_report_status", "source_id", "provider_match_id", "rows_reported", "contexts_checked", "contexts_available", "contexts_missing_optional", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "report_path", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if key.endswith('_enabled') else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

