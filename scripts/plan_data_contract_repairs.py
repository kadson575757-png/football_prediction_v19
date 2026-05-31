# -*- coding: utf-8 -*-
"""Phase 12.3 data contract repair plan.

Diagnostic/foundation only. No source data files are modified; optional previews
are written only under outputs/repair_preview.
"""
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

from audit_data_contracts import discover_csv_files  # noqa: E402
from football_prediction_v19.data_contracts import summarize_data_quality_by_file_type  # noqa: E402
from football_prediction_v19.data_repair import (  # noqa: E402
    RepairAction,
    build_repair_plan_for_dataframe,
    write_repair_preview,
)

OUTPUT_CSV = "data_contract_repair_plan.csv"
OUTPUT_MD = "data_contract_repair_plan.md"


def discover_from_roots(base_root: Path, input_roots: list[str]) -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for root_arg in input_roots:
        root = Path(root_arg)
        if not root.is_absolute():
            root = base_root / root
        if root.is_file() and root.suffix.lower() == ".csv":
            candidates = [root]
        elif root.exists():
            candidates = sorted(root.glob("*.csv"))
        else:
            candidates = []
        for path in candidates:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(path)
    if not paths and input_roots == ["data/raw", "data/processed", "data"]:
        paths = discover_csv_files(base_root)
    return paths


def _safe_read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def build_plan(
    paths: list[Path],
    *,
    include_ready: bool = False,
    write_preview: bool = False,
    repair_preview_dir: Path = ROOT / "outputs" / "repair_preview",
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in paths:
        df = _safe_read(path)
        summary = summarize_data_quality_by_file_type(path, df)
        actions = build_repair_plan_for_dataframe(path, df, summary=summary)
        for action in actions:
            if action.issue_category == "READY_NO_ACTION" and not include_ready:
                continue
            preview = None
            if write_preview:
                preview = write_repair_preview(path, df, action, output_dir=repair_preview_dir)
            row = action.to_dict()
            if preview is not None:
                row["preview_output_path"] = str(preview)
            rows.append(row)
    return pd.DataFrame(rows)


def recommendation(plan: pd.DataFrame) -> str:
    if plan.empty:
        return "INCONCLUSIVE_NO_REPAIR_PLAN"
    if not plan[
        (plan["risk_level"] == "HIGH")
        & (plan["issue_category"].astype(str).str.startswith("HISTORICAL_"))
    ].empty:
        return "FIX_HIGH_RISK_HISTORICAL_DATA_FIRST"
    fixture_blocking = (
        plan["blocking"].astype(bool)
        if "blocking" in plan.columns
        else pd.Series(True, index=plan.index)
    )
    if not plan[(plan["issue_category"] == "EMPTY_FIXTURE_FILE") & fixture_blocking].empty:
        return "FIX_EMPTY_FIXTURE_FILES_FIRST"
    if not plan[plan["issue_category"] == "UNKNOWN_CSV_TYPE"].empty:
        return "CLASSIFY_UNKNOWN_CSV_FILES"
    if plan[plan["file_type"] == "XG_CSV"].empty:
        return "ADD_XG_ENRICHMENT_FILES"
    return "READY_FOR_IMPORTER_SKELETONS"


def _section_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(plan: pd.DataFrame, rec: str) -> str:
    high = plan[plan["risk_level"] == "HIGH"] if not plan.empty else pd.DataFrame()
    medium = plan[plan["risk_level"] == "MEDIUM"] if not plan.empty else pd.DataFrame()
    low = plan[plan["risk_level"] == "LOW"] if not plan.empty else pd.DataFrame()
    empty_fixture = plan[plan["issue_category"] == "EMPTY_FIXTURE_FILE"] if not plan.empty else pd.DataFrame()
    empty_fixture_allowed = empty_fixture[
        empty_fixture.get("blocking", pd.Series(False, index=empty_fixture.index)).astype(bool) == False
    ] if not empty_fixture.empty else pd.DataFrame()
    empty_fixture_refresh = empty_fixture[
        empty_fixture.get("blocking", pd.Series(False, index=empty_fixture.index)).astype(bool) == True
    ] if not empty_fixture.empty else pd.DataFrame()
    invalid_hist = plan[plan["issue_category"].astype(str).str.startswith("HISTORICAL_")] if not plan.empty else pd.DataFrame()
    unknown = plan[plan["issue_category"] == "UNKNOWN_CSV_TYPE"] if not plan.empty else pd.DataFrame()
    odds_xg = plan[plan["issue_category"].isin(["ODDS_CONTRACT_MISSING_TRIPLET", "XG_CONTRACT_MISSING_PAIR"])] if not plan.empty else pd.DataFrame()
    previews = plan[plan["preview_output_path"].astype(str).str.strip().ne("")] if "preview_output_path" in plan.columns and not plan.empty else pd.DataFrame()
    cols = ["file_name", "file_type", "issue_category", "issue_detail", "recommended_action", "risk_level", "blocking", "fixture_status", "fixture_status_reason"]
    lines = [
        "# Phase 12.3 Data Contract Repair Plan",
        "",
        "Phase 12.3 is diagnostic/foundation only. No source data files were modified.",
        "",
        "## A. Executive Summary",
        f"- Repair actions: {len(plan)}",
        f"- High-risk items: {len(high)}",
        f"- Medium-risk items: {len(medium)}",
        f"- Low-risk/no-action items: {len(low)}",
        "",
        "## B. High-Risk Repair Items",
    ]
    lines += _section_table(high, cols)
    lines += ["## C. Medium-Risk Repair Items"]
    lines += _section_table(medium, cols)
    lines += ["## D. Low-Risk / No-Action Items"]
    lines += _section_table(low, cols)
    lines += ["## E. Empty Fixture Files Allowed by Policy"]
    lines += _section_table(empty_fixture_allowed, cols)
    lines += ["## F. Empty Fixture Files Requiring Refresh"]
    lines += _section_table(empty_fixture_refresh, cols)
    lines += ["## G. Invalid Historical Match Files"]
    lines += _section_table(invalid_hist, cols)
    lines += ["## H. Unknown CSV Files"]
    lines += _section_table(unknown, cols)
    lines += ["## I. Odds/xG Contract Issues"]
    lines += _section_table(odds_xg, cols)
    lines += ["## J. Preview Repair Outputs"]
    lines += _section_table(previews, ["file_name", "issue_category", "preview_output_path"])
    lines += [
        "## K. Phase 12.4 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    base_root: Path = ROOT,
    input_roots: list[str] | None = None,
    output_dir: Path = ROOT / "outputs" / "diagnostics",
    repair_preview_dir: Path = ROOT / "outputs" / "repair_preview",
    include_ready: bool = False,
    write_preview: bool = False,
) -> tuple[pd.DataFrame, str]:
    input_roots = input_roots or ["data/raw", "data/processed", "data"]
    paths = discover_from_roots(base_root, input_roots)
    plan = build_plan(
        paths,
        include_ready=include_ready,
        write_preview=write_preview,
        repair_preview_dir=repair_preview_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    rec = recommendation(plan)
    markdown = build_markdown(plan, rec)
    plan.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return plan, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-roots", nargs="+", default=["data/raw", "data/processed", "data"])
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--repair-preview-dir", default=str(ROOT / "outputs" / "repair_preview"))
    parser.add_argument("--include-ready", action="store_true")
    parser.add_argument("--write-preview", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan, markdown = run(
        input_roots=args.input_roots,
        output_dir=Path(args.output_dir),
        repair_preview_dir=Path(args.repair_preview_dir),
        include_ready=args.include_ready,
        write_preview=args.write_preview,
    )
    print(f"Wrote {len(plan)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## K. Phase 12.4 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
