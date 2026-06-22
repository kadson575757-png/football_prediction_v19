# -*- coding: utf-8 -*-
"""Build preview-only match analysis Excel workbook."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.match_analysis_excel_export_preview import MatchAnalysisExcelExportConfig, MatchAnalysisExcelExportRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-bundle-dir", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "match_analysis_excel_export"))
    parser.add_argument("--workbook-filename", default="match_analysis_preview_workbook.xlsx")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_match_analysis_excel_export_preview(**kwargs: object) -> dict[str, object]:
    result = MatchAnalysisExcelExportRunner(MatchAnalysisExcelExportConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_match_analysis_excel_export_preview(
        export_bundle_dir=args.export_bundle_dir,
        output_dir=args.output_dir,
        workbook_filename=args.workbook_filename,
        base_dir=args.base_dir,
    )
    for key in [
        "excel_export_status", "workbook_output_path", "workbook_file_exists",
        "sheets_written", "rows_written_total", "network_calls_enabled",
        "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
        "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
