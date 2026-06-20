# -*- coding: utf-8 -*-
"""Build Phase 16.1 analysis input bundle preview."""
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

from build_file_based_importer_dry_run_preview import build_file_based_importer_dry_run_preview  # noqa: E402
from football_prediction_v19.analysis.input_bundle import (  # noqa: E402
    ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH,
    AnalysisInputBundleBuilder,
    AnalysisInputBundleConfig,
    build_manifest_frame,
    build_manifest_markdown,
)

OUTPUT_DIR = ROOT / "outputs" / "analysis_preview" / "input_bundle"
MANIFEST_CSV = "analysis_input_bundle_manifest.csv"
MANIFEST_MD = "analysis_input_bundle_manifest.md"
VALIDATION_CSV = "analysis_input_validation_summary.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--build-missing-importer-preview", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_preview" / "input_bundle").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _default_input(base: Path) -> Path:
    return base / "outputs" / "importer_preview" / "normalized" / "canonical_match_preview.csv"


def _ensure_importer_preview(input_path: Path | None, base: Path, build_missing: bool) -> Path | None:
    if input_path is not None:
        return input_path
    default = _default_input(base)
    if default.exists() or not build_missing:
        return default
    build_file_based_importer_dry_run_preview(output_dir=base / "outputs" / "importer_preview", write_preview=True, base_dir=base)
    return default


def build_analysis_input_bundle_preview(
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    build_missing_importer_preview: bool = True,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    out_dir = _safe_output_dir(output_dir, base)
    if out_dir is None:
        return {
            "analysis_input_bundle_status": ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH,
            "rows_input": 0,
            "rows_ready": 0,
            "network_calls_enabled": False,
            "prediction_logic_enabled": False,
            "betting_logic_enabled": False,
            "bundle_manifest_path": "",
            "bundle_manifest_summary_path": "",
            "analysis_input_preview_path": "",
            "validation_summary_path": "",
            "recommendation": ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH,
        }
    requested_input = Path(input_path) if input_path is not None else None
    if requested_input is not None and not requested_input.is_absolute():
        requested_input = base / requested_input
    resolved_input = _ensure_importer_preview(requested_input, base, build_missing_importer_preview)
    builder = AnalysisInputBundleBuilder(AnalysisInputBundleConfig(input_path=resolved_input, output_dir=out_dir, write_preview=write_preview, base_dir=base))
    result, _ready, validation = builder.build()
    manifest = build_manifest_frame(result)
    manifest_path = ""
    manifest_md_path = ""
    validation_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = (out_dir / MANIFEST_CSV).resolve()
        manifest_md = (out_dir / MANIFEST_MD).resolve()
        validation_file = (out_dir / VALIDATION_CSV).resolve()
        manifest.to_csv(manifest_file, index=False)
        manifest_md.write_text(build_manifest_markdown(result), encoding="utf-8")
        validation.to_csv(validation_file, index=False)
        manifest_path = str(manifest_file)
        manifest_md_path = str(manifest_md)
        validation_path = str(validation_file)
    return {
        "analysis_input_bundle_status": result.bundle_status,
        "rows_input": result.rows_input,
        "rows_ready": result.rows_ready,
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "bundle_manifest_path": manifest_path,
        "bundle_manifest_summary_path": manifest_md_path,
        "analysis_input_preview_path": result.output_path,
        "validation_summary_path": validation_path,
        "recommendation": result.recommendation,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_analysis_input_bundle_preview(
        input_path=args.input,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        build_missing_importer_preview=args.build_missing_importer_preview,
        base_dir=args.base_dir,
    )
    for key in ["analysis_input_bundle_status", "rows_input", "rows_ready", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "bundle_manifest_path", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if key.endswith('_enabled') else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

