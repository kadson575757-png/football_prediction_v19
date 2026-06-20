# -*- coding: utf-8 -*-
"""Build and audit Bundesliga 2024 analysis export layer closure."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_analysis_export_layer_closure import run as run_closure, summarize_export_layer  # noqa: E402
from build_analysis_excel_workbook_preview import build_analysis_excel_workbook_preview  # noqa: E402

MANIFEST_ID = "trusted_xg_understat_bundesliga_2024_manual_xg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "analysis_export_preview"))
    parser.add_argument("--xg-preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def run_workflow(
    manifest: str | Path,
    preview_dir: str | Path,
    xg_preview_dir: str | Path,
    output_dir: str | Path,
    *,
    window: int = 5,
) -> dict[str, object]:
    build_analysis_excel_workbook_preview(
        manifest=manifest,
        manifest_id=MANIFEST_ID,
        window=window,
        output_dir=preview_dir,
        write_preview=True,
        base_dir=ROOT,
    )
    table, _markdown, rec = run_closure(
        manifest=manifest,
        manifest_id=MANIFEST_ID,
        window=window,
        preview_dir=preview_dir,
        xg_preview_dir=xg_preview_dir,
        output_dir=output_dir,
        base_dir=ROOT,
    )
    return summarize_export_layer(table, rec) | {"manifest_id": MANIFEST_ID}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.manifest, args.preview_dir, args.xg_preview_dir, args.output_dir, window=args.window)
    for key in [
        "export_layer_status",
        "manifest_id",
        "export_bundle_status",
        "excel_workbook_status",
        "xg_reporting_layer_status",
        "model_integration_status",
        "recommendation",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
