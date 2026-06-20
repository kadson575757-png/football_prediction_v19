# -*- coding: utf-8 -*-
"""Build Phase 16.2 single-match analysis report preview."""
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

from build_analysis_input_bundle_preview import build_analysis_input_bundle_preview  # noqa: E402
from football_prediction_v19.analysis.single_match_report import (  # noqa: E402
    SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH,
    SingleMatchAnalysisReportBuilder,
    SingleMatchAnalysisReportConfig,
    build_manifest_frame,
)

OUTPUT_DIR = ROOT / "outputs" / "analysis_preview" / "single_match_report"
MANIFEST_CSV = "single_match_analysis_report_manifest.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None)
    parser.add_argument("--match-id", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--build-missing-input-bundle", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_preview" / "single_match_report").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _default_input(base: Path) -> Path:
    return base / "outputs" / "analysis_preview" / "input_bundle" / "canonical_match_analysis_input_preview.csv"


def _ensure_input_bundle(input_path: Path | None, base: Path, build_missing: bool) -> Path | None:
    if input_path is not None:
        return input_path
    default = _default_input(base)
    if default.exists() or not build_missing:
        return default
    build_analysis_input_bundle_preview(output_dir=base / "outputs" / "analysis_preview" / "input_bundle", write_preview=True, base_dir=base)
    return default


def build_single_match_analysis_report_preview(
    *,
    input_path: str | Path | None = None,
    match_id: str | None = None,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    build_missing_input_bundle: bool = True,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    out_dir = _safe_output_dir(output_dir, base)
    if out_dir is None:
        return {
            "single_match_report_status": SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH,
            "source_id": "",
            "provider_match_id": str(match_id or ""),
            "rows_input": 0,
            "rows_reported": 0,
            "network_calls_enabled": False,
            "prediction_logic_enabled": False,
            "betting_logic_enabled": False,
            "report_path": "",
            "summary_path": "",
            "manifest_path": "",
            "recommendation": SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH,
        }
    requested_input = Path(input_path) if input_path is not None else None
    if requested_input is not None and not requested_input.is_absolute():
        requested_input = base / requested_input
    resolved_input = _ensure_input_bundle(requested_input, base, build_missing_input_bundle)
    builder = SingleMatchAnalysisReportBuilder(SingleMatchAnalysisReportConfig(input_path=resolved_input, match_id=match_id, output_dir=out_dir, write_preview=write_preview, base_dir=base))
    result, _summary, _markdown = builder.build()
    manifest_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = (out_dir / MANIFEST_CSV).resolve()
        build_manifest_frame(result).to_csv(manifest_file, index=False)
        manifest_path = str(manifest_file)
    return {
        "single_match_report_status": result.report_status,
        "source_id": result.source_id,
        "provider_match_id": result.provider_match_id,
        "rows_input": result.rows_input,
        "rows_reported": result.rows_reported,
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "report_path": result.report_path,
        "summary_path": result.summary_path,
        "manifest_path": manifest_path,
        "recommendation": result.recommendation,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_single_match_analysis_report_preview(
        input_path=args.input,
        match_id=args.match_id,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        build_missing_input_bundle=args.build_missing_input_bundle,
        base_dir=args.base_dir,
    )
    for key in ["single_match_report_status", "source_id", "provider_match_id", "rows_input", "rows_reported", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "report_path", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if key.endswith('_enabled') else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

