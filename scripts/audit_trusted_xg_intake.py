# -*- coding: utf-8 -*-
"""Phase 13.3 trusted xG source intake compatibility audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.trusted_xg_intake import (  # noqa: E402
    TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA,
    TRUSTED_XG_INTAKE_BLOCKED_MISSING_XG_COVERAGE,
    TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH,
    TRUSTED_XG_INTAKE_NO_SOURCES_FOUND,
    TRUSTED_XG_INTAKE_READY_FOR_FILL_PREVIEW,
    TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW,
    build_trusted_xg_intake_report,
    discover_trusted_xg_sources,
    trusted_xg_intake_recommendation,
)

OUTPUT_CSV = "trusted_xg_intake_summary.csv"
OUTPUT_MD = "trusted_xg_intake_summary.md"
OUTPUT_COMMANDS = "trusted_xg_next_commands.ps1"


def _serialize_lists(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    for col in ("blocking_reasons", "warning_notes"):
        if col in out.columns:
            out[col] = out[col].map(lambda value: " | ".join(value) if isinstance(value, list) else str(value or ""))
    return out


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 40) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ";") for col in cols) + " |")
    lines.append("")
    return lines


def build_command_list(table: pd.DataFrame) -> str:
    commands = []
    for command in table.get("recommended_command", pd.Series(dtype=str)).astype(str):
        if command.strip():
            commands.append(command.strip())
    if not commands:
        return "\n".join([
            "# Use scripts/import_trusted_xg_source.py with a local export or explicit URL.",
            "python scripts/import_trusted_xg_source.py --source \"C:\\path\\to\\trusted_xg_export.csv\" --output-name trusted_xg_export.csv",
            "# Place a real trusted xG source CSV in data/trusted_xg_sources/",
            "# Expected match-pair columns: date, home_team, away_team, home_xg, away_xg",
            "python scripts/audit_trusted_xg_intake.py --write-command-list",
            "",
        ])
    return "\n".join(["# Phase 13.3 trusted xG next commands"] + commands + [""])


def build_markdown(table: pd.DataFrame, rec: str, source_dir: Path) -> str:
    serial = _serialize_lists(table)
    labels = serial["intake_label"].astype(str) if not serial.empty else pd.Series(dtype=str)
    no_sources = int(labels.eq(TRUSTED_XG_INTAKE_NO_SOURCES_FOUND).sum())
    valid = serial[serial.get("valid_source", False).astype(bool)] if "valid_source" in serial.columns else pd.DataFrame()
    invalid = serial[labels == TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA] if not serial.empty else pd.DataFrame()
    fill = serial[labels == TRUSTED_XG_INTAKE_READY_FOR_FILL_PREVIEW] if not serial.empty else pd.DataFrame()
    promotion = serial[labels == TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW] if not serial.empty else pd.DataFrame()
    missing = serial[labels == TRUSTED_XG_INTAKE_BLOCKED_MISSING_XG_COVERAGE] if not serial.empty else pd.DataFrame()
    no_target = serial[labels == TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH] if not serial.empty else pd.DataFrame()
    cols = [
        "source_file",
        "detected_schema",
        "source_rows",
        "best_target_file",
        "best_rows_template",
        "best_rows_filled",
        "best_rows_missing_xg",
        "best_fill_coverage_pct",
        "best_promotion_label",
        "intake_label",
    ]
    lines = [
        "# Phase 13.3 Trusted xG Source Intake Audit",
        "",
        "Phase 13.3 is diagnostic/foundation only. No xG values were inferred or invented, and no model behavior was changed.",
        "",
        "## A. Executive Summary",
        f"- source directory: {source_dir}",
        f"- trusted xG source files found: {0 if no_sources else len(serial)}",
        f"- valid source files: {len(valid)}",
        f"- invalid source files: {len(invalid)}",
        f"- sources ready for fill preview: {len(fill)}",
        f"- sources ready for promotion preview: {len(promotion)}",
        f"- sources blocked by missing coverage: {len(missing)}",
        f"- sources blocked by no target match: {len(no_target)}",
        "",
        "## B. Trusted xG Intake Results",
    ]
    lines += _section_table(serial, cols)
    lines += ["## C. Best Target Matches"]
    lines += _section_table(serial[serial["best_target_file"].astype(str).ne("")] if not serial.empty else pd.DataFrame(), cols)
    lines += ["## D. Blocked Sources"]
    lines += _section_table(serial[labels.str.contains("BLOCKED|NO_SOURCES", regex=True, na=False)] if not serial.empty else pd.DataFrame(), cols + ["blocking_reasons"])
    lines += ["## E. Recommended Next Commands"]
    command_text = build_command_list(serial)
    lines += ["```powershell", command_text.rstrip(), "```", ""]
    lines += [
        "## F. Safety Checks",
        "- No source CSV files modified in place.",
        "- No xG values inferred or invented.",
        "- No scraping, API calls, credentials, or network access required.",
        "- No model, probability, recommended-market, betting, staking, ROI, market_tier, or SUPER_A_TIER behavior changed.",
        "",
        "## G. Phase 13.3 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(source_dir: Path, output_dir: Path, write_command_list: bool = False) -> tuple[pd.DataFrame, str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_trusted_xg_intake_report(source_dir)
    rec = trusted_xg_intake_recommendation(table)
    markdown = build_markdown(table, rec, source_dir)
    _serialize_lists(table).to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    if write_command_list:
        (output_dir / OUTPUT_COMMANDS).write_text(build_command_list(table), encoding="utf-8")
    return table, markdown, rec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default=str(ROOT / "data" / "trusted_xg_sources"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--write-command-list", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(Path(args.source_dir), Path(args.output_dir), write_command_list=args.write_command_list)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    if args.write_command_list:
        print(f"Wrote command list to {Path(args.output_dir) / OUTPUT_COMMANDS}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
