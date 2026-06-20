# -*- coding: utf-8 -*-
"""Build and audit Bundesliga 2024 analysis Excel workbook preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_analysis_excel_workbook_preview import run as run_audit  # noqa: E402
from build_analysis_excel_workbook_preview import build_analysis_excel_workbook_preview  # noqa: E402

MANIFEST_ID = "trusted_xg_understat_bundesliga_2024_manual_xg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_export_preview"))
    return parser


def run_workflow(manifest: str | Path, output_dir: str | Path, *, window: int = 5) -> dict[str, object]:
    summary = build_analysis_excel_workbook_preview(
        manifest=manifest,
        manifest_id=MANIFEST_ID,
        window=window,
        output_dir=output_dir,
        write_preview=True,
        base_dir=ROOT,
    )
    _table, _markdown, rec = run_audit(
        workbook=summary.get("workbook_path") or None,
        output_dir=ROOT / "outputs" / "diagnostics",
        base_dir=ROOT,
    )
    return {**summary, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.manifest, args.output_dir, window=args.window)
    for key in ["excel_workbook_status", "manifest_id", "sheets_written", "workbook_path", "recommendation"]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
