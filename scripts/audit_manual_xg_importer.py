# -*- coding: utf-8 -*-
"""Phase 12.9 manual xG importer readiness audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_csv import import_manual_xg_csv  # noqa: E402

OUTPUT_CSV = "manual_xg_importer_audit_summary.csv"
OUTPUT_MD = "manual_xg_importer_audit_summary.md"


def discover_manual_xg_candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "templates" / "manual_xg_template.csv",
        root / "data" / "raw" / "*xg*.csv",
        root / "data" / "*xg*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            out.append(path)
    return out


def audit_file(path: Path, preview_dir: Path) -> dict[str, object]:
    try:
        result = import_manual_xg_csv(path, output_dir=preview_dir, strict=True, write_preview=False)
    except Exception as exc:
        return {
            "file_path": str(path),
            "file_name": path.name,
            "rows_read": 0,
            "xg_schema": "",
            "xg_contract_label": "",
            "xg_production_ready": False,
            "template_demo": "template" in path.name.lower() or "sample" in path.name.lower(),
            "import_ready": False,
            "preview_available": False,
            "validation_errors": str(exc),
            "warning_notes": "",
        }
    template_demo = "template" in path.name.lower() or "sample" in path.name.lower()
    import_ready = not result.validation_errors and not template_demo and result.xg_production_ready
    return {
        "file_path": str(path),
        "file_name": path.name,
        "rows_read": result.rows_read,
        "xg_schema": result.xg_schema,
        "xg_contract_label": result.xg_contract_label,
        "xg_production_ready": result.xg_production_ready,
        "template_demo": template_demo,
        "import_ready": import_ready,
        "preview_available": not result.validation_errors,
        "validation_errors": " | ".join(result.validation_errors),
        "warning_notes": " | ".join(result.warning_notes),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_MANUAL_XG_FILES"
    invalid = table[table["validation_errors"].astype(str).str.strip().ne("")]
    ready = table[table["import_ready"] == True]
    templates = table[table["template_demo"] == True]
    if not ready.empty:
        return "READY_FOR_MANUAL_XG_IMPORT_PREVIEW"
    if not templates.empty:
        return "ADD_PRODUCTION_MANUAL_XG_FILE"
    if not invalid.empty:
        return "FIX_MANUAL_XG_CONTRACT_ERRORS"
    return "INCONCLUSIVE_NO_MANUAL_XG_FILES"


def _section_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    ready = table[table["import_ready"] == True] if not table.empty else pd.DataFrame()
    templates = table[table["template_demo"] == True] if not table.empty else pd.DataFrame()
    invalid = table[table["validation_errors"].astype(str).str.strip().ne("")] if not table.empty else pd.DataFrame()
    lines = [
        "# Phase 12.9 Manual xG Importer Audit",
        "",
        "Phase 12.9 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- Files scanned: {len(table)}",
        f"- Import-ready manual xG files: {len(ready)}",
        f"- Template/demo files: {len(templates)}",
        f"- Invalid manual xG files: {len(invalid)}",
        f"- Preview outputs available: {int(table['preview_available'].sum()) if not table.empty else 0}",
        "",
        "## B. Manual xG Import-Ready Files",
    ]
    lines += _section_table(ready, ["file_name", "rows_read", "xg_schema", "xg_production_ready"])
    lines += ["## C. Template / Demo xG Files"]
    lines += _section_table(templates, ["file_name", "rows_read", "xg_schema", "warning_notes"])
    lines += ["## D. Invalid Manual xG Files"]
    lines += _section_table(invalid, ["file_name", "rows_read", "validation_errors"])
    lines += [
        "## E. Safety Checks",
        "- No source CSV modified.",
        "- No xG values inferred or invented.",
        "- No network calls, credentials, betting, staking, ROI, probability, market-tier, or recommended-market logic changed.",
        "",
        "## F. Phase 12.9 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir = root / "outputs" / "xg_import_preview"
    table = pd.DataFrame([audit_file(path, preview_dir) for path in discover_manual_xg_candidates(root)])
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(root=Path(args.root), output_dir=Path(args.output_dir))
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## F. Phase 12.9 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
