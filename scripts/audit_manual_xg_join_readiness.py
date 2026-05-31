# -*- coding: utf-8 -*-
"""Phase 12.10 manual xG join readiness audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_csv import import_manual_xg_csv  # noqa: E402
from football_prediction_v19.xg_join_preview import (  # noqa: E402
    JOIN_READY,
    JOIN_READY_WITH_WARNINGS,
    run_xg_join_preview,
)

OUTPUT_CSV = "manual_xg_join_readiness_summary.csv"
OUTPUT_MD = "manual_xg_join_readiness_summary.md"


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen and path.exists():
            seen.add(resolved)
            out.append(path)
    return out


def discover_xg_candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "manual_xg" / "*.csv",
        root / "data" / "raw" / "*xg*.csv",
        root / "data" / "*xg*.csv",
        root / "data" / "templates" / "manual_xg_template.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def discover_targets(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "processed" / "real_matches_clean.csv",
        root / "data" / "processed" / "matches_clean_with_totals.csv",
        root / "data" / "processed" / "*_clean.csv",
        root / "data" / "upcoming*_fixtures*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def build_table(root: Path, output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    xg_candidates = discover_xg_candidates(root)
    targets = discover_targets(root)
    for xg in xg_candidates:
        import_result = import_manual_xg_csv(xg, write_preview=False)
        production_candidate = import_result.xg_production_ready and "template" not in xg.name.lower() and "sample" not in xg.name.lower()
        for target in targets:
            try:
                result = run_xg_join_preview(xg, target, output_dir=output_dir, target_type="auto", write_preview=False)
                row = result.to_dict()
            except Exception as exc:
                row = {
                    "xg_source_path": str(xg),
                    "target_path": str(target),
                    "target_type": "auto",
                    "rows_xg": import_result.rows_read,
                    "rows_target": 0,
                    "matched_rows": 0,
                    "unmatched_xg_rows": 0,
                    "unmatched_target_rows": 0,
                    "duplicate_xg_keys": 0,
                    "duplicate_target_keys": 0,
                    "ambiguous_matches": 0,
                    "join_coverage_pct": 0.0,
                    "join_quality_label": "JOIN_INVALID_INPUT",
                    "output_path": "",
                    "warning_notes": [str(exc)],
                }
            row["xg_file_name"] = xg.name
            row["target_file_name"] = target.name
            row["production_xg_candidate"] = production_candidate
            rows.append(row)
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_JOIN_CANDIDATES"
    production = table[table["production_xg_candidate"] == True]
    if production.empty:
        return "ADD_PRODUCTION_MANUAL_XG_FILE"
    if (production["duplicate_xg_keys"] > 0).any():
        return "FIX_DUPLICATE_XG_KEYS"
    if (production["duplicate_target_keys"] > 0).any():
        return "FIX_TARGET_JOIN_KEYS"
    if production["join_quality_label"].isin([JOIN_READY, JOIN_READY_WITH_WARNINGS]).any():
        return "READY_FOR_MANUAL_XG_JOIN_PIPELINE"
    if not production.empty:
        return "FIX_XG_JOIN_KEYS"
    return "INCONCLUSIVE_NO_JOIN_CANDIDATES"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 50) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    df = df.head(limit)
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    ready = table[table["join_quality_label"] == JOIN_READY] if not table.empty else pd.DataFrame()
    warn = table[table["join_quality_label"] == JOIN_READY_WITH_WARNINGS] if not table.empty else pd.DataFrame()
    blocked = table[table["join_quality_label"].astype(str).str.contains("BLOCKED|INVALID", regex=True)] if not table.empty else pd.DataFrame()
    low = table[table["join_quality_label"].isin(["JOIN_LOW_COVERAGE", "JOIN_NO_MATCHES"])] if not table.empty else pd.DataFrame()
    dupes = table[(table["duplicate_xg_keys"] > 0) | (table["duplicate_target_keys"] > 0)] if not table.empty else pd.DataFrame()
    lines = [
        "# Phase 12.10 Manual xG Join Readiness",
        "",
        "Phase 12.10 is diagnostic/foundation only. No xG values were inferred, invented, or written back to source data.",
        "",
        "## A. Executive Summary",
        f"- xG candidate files scanned: {table['xg_file_name'].nunique() if not table.empty else 0}",
        f"- target files scanned: {table['target_file_name'].nunique() if not table.empty else 0}",
        f"- join previews attempted: {len(table)}",
        f"- JOIN_READY count: {len(ready)}",
        f"- JOIN_READY_WITH_WARNINGS count: {len(warn)}",
        f"- blocked count: {len(blocked)}",
        f"- low coverage/no matches count: {len(low)}",
        "",
        "## B. Join-Ready Manual xG Sources",
    ]
    cols = ["xg_file_name", "target_file_name", "matched_rows", "join_coverage_pct", "join_quality_label"]
    lines += _section_table(ready, cols)
    lines += ["## C. Join-Ready With Warnings"]
    lines += _section_table(warn, cols)
    lines += ["## D. Blocked Join Previews"]
    lines += _section_table(blocked, cols + ["duplicate_xg_keys", "duplicate_target_keys"])
    lines += ["## E. Low Coverage / No Match Previews"]
    lines += _section_table(low, cols)
    lines += ["## F. Duplicate Key Diagnostics"]
    lines += _section_table(dupes, ["xg_file_name", "target_file_name", "duplicate_xg_keys", "duplicate_target_keys"])
    lines += [
        "## G. Safety Checks",
        "- No source or target CSV modified.",
        "- No xG values inferred, invented, or written back.",
        "- No web/API/credential, betting, staking, ROI, probability, market-tier, or recommended-market logic changed.",
        "",
        "## H. Phase 12.10 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_table(root, root / "outputs" / "xg_join_preview")
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
    print(markdown.split("## H. Phase 12.10 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
